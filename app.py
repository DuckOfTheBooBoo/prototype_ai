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
    """Handle client WebSocket connection."""
    print(f'Socket connected: {request.sid}')
    emit('connected', {'status': 'connected'})


@socketio.on('join_stream')
def handle_join_stream(data):
    """Client sends visitor_id to join or create stream."""
    visitor_id = data.get('visitor_id')
    
    if not visitor_id:
        emit('error', {'message': 'visitor_id required'})
        return
    
    # Map socket to visitor
    socket_to_visitor[request.sid] = visitor_id
    
    # Join the room for this visitor
    join_room(visitor_id)
    
    # Check if visitor already has active stream
    if visitor_id in active_streams:
        # Join existing stream
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].add(request.sid)
        emit('joined_existing_stream', {'status': 'joined'})
        print(f'Socket {request.sid} joined existing stream for visitor {visitor_id}')
    else:
        # Create new stream
        active_streams[visitor_id] = {
            'socket_ids': {request.sid},
            'status': 'active',
            'thread': None
        }
        # Start streaming in background
        thread = socketio.start_background_task(stream_predictions, visitor_id)
        active_streams[visitor_id]['thread'] = thread
        emit('stream_started', {'status': 'started'})
        print(f'Started new stream for visitor {visitor_id}')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and cleanup."""
    sid = request.sid
    visitor_id = socket_to_visitor.get(sid)
    
    if not visitor_id:
        print(f'Socket disconnected: {sid}')
        return
    
    # Remove socket from visitor's stream
    if visitor_id in active_streams:
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].discard(sid)
        
        # If no more sockets, mark stream for cleanup
        if len(stream_info['socket_ids']) == 0:
            stream_info['status'] = 'cleanup'
            print(f'Last socket disconnected, marking stream {visitor_id} for cleanup')
    
    # Remove socket mapping
    if sid in socket_to_visitor:
        del socket_to_visitor[sid]
    
    print(f'Socket disconnected: {sid}')


def stream_predictions(visitor_id):
    """Stream predictions from test data to a specific visitor."""
    try:
        print(f"Loading test data for visitor {visitor_id}...")
        
        # Load test data with corrected paths
        test_trans = pd.read_csv('./content/small_test_transaction.csv')
        test_id = pd.read_csv('./content/ieee-fraud-detection/test_identity.csv')
        
        # Preprocess column names
        test_trans.columns = test_trans.columns.str.replace('-', '_')
        test_id.columns = test_id.columns.str.replace('-', '_')
        
        print("Merging transaction and identity data...")
        test_merged = test_trans.merge(test_id, on='TransactionID', how='left')
        
        print(f"Streaming {len(test_merged)} predictions for visitor {visitor_id}...")
        
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
            
            # Emit to all sockets for this visitor
            socketio.emit('prediction', result, room=visitor_id)
            
            # Random delay between 0.5 and 2.5 seconds
            delay = random.uniform(0.5, 2.5)
            eventlet.sleep(delay)
            
            if (idx + 1) % 100 == 0:
                print(f"Visitor {visitor_id}: Processed {idx + 1}/{len(test_merged)} transactions")
        
        # Stream completed successfully
        print(f"Stream complete for visitor {visitor_id}!")
        socketio.emit('stream_complete', {
            'total': len(test_merged),
            'message': 'All transactions processed'
        }, room=visitor_id)
        
    except Exception as e:
        print(f"Error streaming predictions for visitor {visitor_id}: {e}")
        socketio.emit('stream_error', {'error': str(e)}, room=visitor_id)
    
    finally:
        # Cleanup stream from active_streams
        if visitor_id in active_streams:
            del active_streams[visitor_id]
            print(f"Cleaned up stream for {visitor_id}")


if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    socketio.run(app, host=host, port=port, debug=debug)
