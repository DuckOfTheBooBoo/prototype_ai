from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from fraud_detection import FraudDetector
import os
import pandas as pd
import random
import eventlet
from datetime import datetime
import threading

app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# WebSocket configuration
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

detector = None

# Track active streams per visitor
active_streams = {}  # visitor_id -> {thread, socket_ids, status}
socket_to_visitor = {}  # socket.sid -> visitor_id

# Environment variables for deployment
HF_REPO_ID = os.environ.get('HF_REPO_ID', None)

def get_detector():
    """Lazy load detector to avoid startup delays."""
    global detector
    if detector is None:
        artifact_path = os.path.join('.', 'artifacts') + os.sep
        
        # Check if we should load from HuggingFace
        if HF_REPO_ID:
            print(f"Initializing FraudDetector with HuggingFace models: {HF_REPO_ID}")
            detector = FraudDetector(
                artifact_path=artifact_path,
                hf_repo_id=HF_REPO_ID
            )
        else:
            print("Initializing FraudDetector with local artifacts")
            detector = FraudDetector(artifact_path=artifact_path)
    return detector


@app.route('/predict', methods=['POST'])
def predict():
    """
    Accept single transaction data, return fraud prediction.

    Request: JSON object with transaction features
    Response: JSON with prediction result or error

    HTTP Status Codes:
      - 200: Success
      - 400: No data in request body
      - 422: Data insufficient / shape mismatch
      - 500: Server error
    """
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'No data in request body'
            }), 400

        data = request.get_json()

        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'No data in request body'
            }), 400

        det = get_detector()
        result = det.predict(data)

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Data insufficient or invalid format'
        }), 422

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'An error occurred'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Simple health check for monitoring."""
    return jsonify({'status': 'ok'}), 200


@app.route('/api')
def api_info():
    return jsonify({
        'service': 'Fraud Detection API',
        'version': '1.0',
        'endpoints': {
            'POST /predict': 'Predict fraud for single transaction',
            'GET /health': 'Health check'
        }
    }), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder = app.static_folder
    
    if not static_folder or not os.path.exists(static_folder):
        return jsonify({
            'error': 'Frontend not built',
            'message': 'Please build the frontend first: cd frontend && pnpm build'
        }), 500
    
    if path and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder, 'index.html')
    
    return jsonify({
        'error': 'Frontend not found',
        'message': 'Please build the frontend: cd frontend && pnpm build'
    }), 500


@socketio.on('connect')
def handle_connect():
    print('=' * 80)
    print('🟢 [SOCKETIO] NEW CONNECTION ATTEMPT')
    print(f'🟢 [SOCKETIO] Socket ID: {request.sid}')
    print(f'🟢 [SOCKETIO] Client Address: {request.remote_addr}')
    print(f'🟢 [SOCKETIO] Headers: {dict(request.headers)}')
    print(f'🟢 [SOCKETIO] Transport: {request.environ.get("HTTP_UPGRADE", "polling")}')
    print(f'🟢 [SOCKETIO] X-Forwarded-Proto: {request.headers.get("X-Forwarded-Proto")}')
    print(f'🟢 [SOCKETIO] User-Agent: {request.headers.get("User-Agent")}')
    print('=' * 80)
    emit('connected', {'status': 'connected'})


@socketio.on('join_stream')
def handle_join_stream(data):
    print('🔵 [SOCKETIO] JOIN_STREAM EVENT RECEIVED')
    print(f'🔵 [SOCKETIO] Socket ID: {request.sid}')
    print(f'🔵 [SOCKETIO] Data received: {data}')
    
    visitor_id = data.get('visitor_id')
    
    if not visitor_id:
        print('🔴 [SOCKETIO] ERROR: No visitor_id provided')
        emit('error', {'message': 'visitor_id required'})
        return
    
    print(f'🔵 [SOCKETIO] Visitor ID: {visitor_id}')
    socket_to_visitor[request.sid] = visitor_id
    join_room(visitor_id)
    print(f'🔵 [SOCKETIO] Socket {request.sid} joined room: {visitor_id}')
    
    if visitor_id in active_streams:
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].add(request.sid)
        emit('joined_existing_stream', {'status': 'joined'})
        print(f'🟡 [SOCKETIO] Socket joined existing stream for visitor {visitor_id}')
        print(f'🟡 [SOCKETIO] Active sockets for this visitor: {len(stream_info["socket_ids"])}')
    else:
        active_streams[visitor_id] = {
            'socket_ids': {request.sid},
            'status': 'active',
            'thread': None
        }
        print(f'🟢 [SOCKETIO] Creating NEW stream for visitor {visitor_id}')
        thread = socketio.start_background_task(stream_predictions, visitor_id)
        active_streams[visitor_id]['thread'] = thread
        emit('stream_started', {'status': 'started'})
        print(f'✅ [SOCKETIO] Stream started for visitor {visitor_id}')


@socketio.on('disconnect')
def handle_disconnect():
    print('=' * 80)
    print('🔴 [SOCKETIO] CLIENT DISCONNECTED')
    sid = request.sid
    print(f'🔴 [SOCKETIO] Socket ID: {sid}')
    
    visitor_id = socket_to_visitor.get(sid)
    
    if not visitor_id:
        print(f'🔴 [SOCKETIO] No visitor_id mapped for socket {sid}')
        print('=' * 80)
        return
    
    print(f'🔴 [SOCKETIO] Visitor ID: {visitor_id}')
    
    if visitor_id in active_streams:
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].discard(sid)
        print(f'🔴 [SOCKETIO] Remaining sockets for visitor {visitor_id}: {len(stream_info["socket_ids"])}')
        
        if len(stream_info['socket_ids']) == 0:
            stream_info['status'] = 'cleanup'
            print(f'🔴 [SOCKETIO] Last socket disconnected, marking stream {visitor_id} for cleanup')
    
    if sid in socket_to_visitor:
        del socket_to_visitor[sid]
    
    print('=' * 80)


def stream_predictions(visitor_id):
    try:
    try:
        print('📊 ' + '=' * 78)
        print(f'📊 [STREAM] Starting prediction stream for visitor: {visitor_id}')
        
        print(f'📊 [DEBUG] Current working directory: {os.getcwd()}')
        print(f'📊 [DEBUG] Checking if content directory exists...')
        if os.path.exists('./content'):
            print(f'📊 [DEBUG] ./content EXISTS')
            print(f'📊 [DEBUG] Contents of ./content:')
            for item in os.listdir('./content'):
                print(f'📊 [DEBUG]   - {item}')
        else:
            print(f'📊 [DEBUG] ./content DOES NOT EXIST')
            print(f'📊 [DEBUG] Current directory contents:')
            for item in os.listdir('.'):
                print(f'📊 [DEBUG]   - {item}')
        
        print(f'📊 [DEBUG] File check: ./content/small_test_transaction.csv exists = {os.path.exists("./content/small_test_transaction.csv")}')
        print(f'📊 [DEBUG] File check: ./content/ieee-fraud-detection/test_identity.csv exists = {os.path.exists("./content/ieee-fraud-detection/test_identity.csv")}')
        
        print(f'📊 [STREAM] Loading test data...')
        test_trans = pd.read_csv('./content/small_test_transaction.csv')
        test_id = pd.read_csv('./content/ieee-fraud-detection/test_identity.csv')
        
        test_trans.columns = test_trans.columns.str.replace('-', '_')
        test_id.columns = test_id.columns.str.replace('-', '_')
        
        print(f'📊 [STREAM] Merging transaction and identity data...')
        test_merged = test_trans.merge(test_id, on='TransactionID', how='left')
        
        print(f'📊 [STREAM] Will stream {len(test_merged)} predictions')
        print('📊 ' + '=' * 78)
        
        for idx, row in test_merged.iterrows():
            # Check if stream should stop
            stream_info = active_streams.get(visitor_id)
            if not stream_info or stream_info['status'] == 'cleanup':
                print(f"Stream {visitor_id} stopped early (cleanup requested)")
                break
            
            # Process transaction
            transaction_data = row.to_dict()
            
            det = get_detector()
            result = det.predict(transaction_data)
            
            result['TransactionID'] = row['TransactionID']
            result['TransactionAmt'] = row['TransactionAmt']
            result['timestamp'] = datetime.now().isoformat()
            
            socketio.emit('prediction', result, room=visitor_id)
            
            delay = random.uniform(0.5, 2.5)
            eventlet.sleep(delay)
            
            if (idx + 1) % 100 == 0:
                print(f'📊 [STREAM] Progress for {visitor_id}: {idx + 1}/{len(test_merged)} transactions')
            elif (idx + 1) % 10 == 0:
                print(f'📊 [STREAM] Visitor {visitor_id}: {idx + 1} transactions sent')
        
        print('✅ ' + '=' * 78)
        print(f'✅ [STREAM] Stream complete for visitor {visitor_id}!')
        print(f'✅ [STREAM] Total transactions processed: {len(test_merged)}')
        print('✅ ' + '=' * 78)
        socketio.emit('stream_complete', {
            'total': len(test_merged),
            'message': 'All transactions processed'
        }, room=visitor_id)
        
    except Exception as e:
        print('🔴 ' + '=' * 78)
        print(f'🔴 [STREAM] ERROR in stream for visitor {visitor_id}')
        print(f'🔴 [STREAM] Error: {e}')
        print(f'🔴 [STREAM] Error type: {type(e).__name__}')
        import traceback
        print(f'🔴 [STREAM] Traceback:')
        traceback.print_exc()
        print('🔴 ' + '=' * 78)
        socketio.emit('stream_error', {'error': str(e)}, room=visitor_id)
    
    finally:
        if visitor_id in active_streams:
            del active_streams[visitor_id]
            print(f'🧹 [STREAM] Cleaned up stream for {visitor_id}')


if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    print('🚀 ' + '=' * 78)
    print('🚀 [STARTUP] Starting Flask-SocketIO server')
    print(f'🚀 [STARTUP] Host: {host}')
    print(f'🚀 [STARTUP] Port: {port}')
    print(f'🚀 [STARTUP] Debug: {debug}')
    print(f'🚀 [STARTUP] HF_REPO_ID: {HF_REPO_ID or "Not set (using local artifacts)"}')
    print('🚀 ' + '=' * 78)

    socketio.run(app, host=host, port=port, debug=debug)
