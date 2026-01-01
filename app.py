import logging
import os
import random
from datetime import datetime
import sys

import eventlet
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room

from fraud_detection import FraudDetector

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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)

logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('eventlet').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# DEBUG: Check filesystem at startup
logger.info("=" * 80)
logger.info("🔍 [STARTUP DEBUG] Filesystem Check")
logger.info(f"🔍 [STARTUP DEBUG] Current directory: {os.getcwd()}")
logger.info("🔍 [STARTUP DEBUG] Directory contents:")
for item in sorted(os.listdir('.')):
    item_path = os.path.join('.', item)
    if os.path.isdir(item_path):
        logger.info(f"🔍 [STARTUP DEBUG]   📁 {item}/")
    else:
        logger.info(f"🔍 [STARTUP DEBUG]   📄 {item}")

if os.path.exists('./content'):
    logger.info("🔍 [STARTUP DEBUG] ✅ ./content EXISTS!")
    logger.info("🔍 [STARTUP DEBUG] Contents of ./content:")
    for item in sorted(os.listdir('./content')):
        item_path = os.path.join('./content', item)
        if os.path.isdir(item_path):
            logger.info(f"🔍 [STARTUP DEBUG]     📁 {item}/")
        else:
            size = os.path.getsize(item_path)
            logger.info(f"🔍 [STARTUP DEBUG]     📄 {item} ({size:,} bytes)")
    
    # Check for specific files
    files_to_check = [
        './content/small_test_transaction.csv',
        './content/ieee-fraud-detection/test_identity.csv'
    ]
    for filepath in files_to_check:
        exists = os.path.exists(filepath)
        if exists:
            size = os.path.getsize(filepath)
            logger.info(f"🔍 [STARTUP DEBUG] ✅ {filepath} EXISTS ({size:,} bytes)")
        else:
            logger.info(f"🔍 [STARTUP DEBUG] ❌ {filepath} DOES NOT EXIST")
else:
    logger.info("🔍 [STARTUP DEBUG] ❌ ./content DOES NOT EXIST")
logger.info("=" * 80)


def get_detector():
    """Lazy load detector to avoid startup delays."""
    global detector
    if detector is None:
        artifact_path = os.path.join('.', 'artifacts') + os.sep
        
        # Check if we should load from HuggingFace
        if HF_REPO_ID:
            logger.info(f"Initializing FraudDetector with HuggingFace models: {HF_REPO_ID}")
            detector = FraudDetector(
                artifact_path=artifact_path,
                hf_repo_id=HF_REPO_ID
            )
        else:
            logger.info("Initializing FraudDetector with local artifacts")
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

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Data insufficient or invalid format'
        }), 422

    except Exception:
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
    logger.info('=' * 80)
    logger.info('🟢 [SOCKETIO] NEW CONNECTION ATTEMPT')
    logger.info(f'🟢 [SOCKETIO] Socket ID: {request.sid}')
    logger.info(f'🟢 [SOCKETIO] Client Address: {request.remote_addr}')
    logger.info(f'🟢 [SOCKETIO] Headers: {dict(request.headers)}')
    logger.info(f'🟢 [SOCKETIO] Transport: {request.environ.get("HTTP_UPGRADE", "polling")}')
    logger.info(f'🟢 [SOCKETIO] X-Forwarded-Proto: {request.headers.get("X-Forwarded-Proto")}')
    logger.info(f'🟢 [SOCKETIO] User-Agent: {request.headers.get("User-Agent")}')
    logger.info('=' * 80)
    emit('connected', {'status': 'connected'})


@socketio.on('join_stream')
def handle_join_stream(data):
    logger.info('🔵 [SOCKETIO] JOIN_STREAM EVENT RECEIVED')
    logger.info(f'🔵 [SOCKETIO] Socket ID: {request.sid}')
    logger.info(f'🔵 [SOCKETIO] Data received: {data}')
    
    visitor_id = data.get('visitor_id')
    
    if not visitor_id:
        logger.info('🔴 [SOCKETIO] ERROR: No visitor_id provided')
        emit('error', {'message': 'visitor_id required'})
        return
    
    logger.info(f'🔵 [SOCKETIO] Visitor ID: {visitor_id}')
    socket_to_visitor[request.sid] = visitor_id
    join_room(visitor_id)
    logger.info(f'🔵 [SOCKETIO] Socket {request.sid} joined room: {visitor_id}')
    
    if visitor_id in active_streams:
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].add(request.sid)
        emit('joined_existing_stream', {'status': 'joined'})
        logger.info(f'🟡 [SOCKETIO] Socket joined existing stream for visitor {visitor_id}')
        logger.info(f'🟡 [SOCKETIO] Active sockets for this visitor: {len(stream_info["socket_ids"])}')
    else:
        active_streams[visitor_id] = {
            'socket_ids': {request.sid},
            'status': 'active',
            'thread': None
        }
        logger.info(f'🟢 [SOCKETIO] Creating NEW stream for visitor {visitor_id}')
        thread = socketio.start_background_task(stream_predictions, visitor_id)
        active_streams[visitor_id]['thread'] = thread
        emit('stream_started', {'status': 'started'})
        logger.info(f'✅ [SOCKETIO] Stream started for visitor {visitor_id}')


@socketio.on('disconnect')
def handle_disconnect():
    logger.info('=' * 80)
    logger.info('🔴 [SOCKETIO] CLIENT DISCONNECTED')
    sid = request.sid
    logger.info(f'🔴 [SOCKETIO] Socket ID: {sid}')
    
    visitor_id = socket_to_visitor.get(sid)
    
    if not visitor_id:
        logger.info(f'🔴 [SOCKETIO] No visitor_id mapped for socket {sid}')
        logger.info('=' * 80)
        return
    
    logger.info(f'🔴 [SOCKETIO] Visitor ID: {visitor_id}')
    
    if visitor_id in active_streams:
        stream_info = active_streams[visitor_id]
        stream_info['socket_ids'].discard(sid)
        logger.info(f'🔴 [SOCKETIO] Remaining sockets for visitor {visitor_id}: {len(stream_info["socket_ids"])}')
        
        if len(stream_info['socket_ids']) == 0:
            stream_info['status'] = 'cleanup'
            logger.info(f'🔴 [SOCKETIO] Last socket disconnected, marking stream {visitor_id} for cleanup')
    
    if sid in socket_to_visitor:
        del socket_to_visitor[sid]
    
    logger.info('=' * 80)


def stream_predictions(visitor_id):
    try:
        logger.info('📊 ' + '=' * 78)
        logger.info(f'📊 [STREAM] Starting prediction stream for visitor: {visitor_id}')
        
        logger.debug(f'📊 [DEBUG] Current working directory: {os.getcwd()}')
        logger.debug('📊 [DEBUG] Checking if content directory exists...')
        if os.path.exists('./content'):
            logger.debug('📊 [DEBUG] ./content EXISTS')
            logger.debug('📊 [DEBUG] Contents of ./content:')
            for item in os.listdir('./content'):
                logger.debug(f'📊 [DEBUG]   - {item}')
        else:
            logger.debug('📊 [DEBUG] ./content DOES NOT EXIST')
            logger.debug('📊 [DEBUG] Current directory contents:')
            for item in os.listdir('.'):
                logger.debug(f'📊 [DEBUG]   - {item}')
        
        csv1_path = os.path.join(os.getcwd(), 'content', 'small_test_transaction.csv')
        csv2_path = os.path.join(os.getcwd(), 'content', 'ieee-fraud-detection', 'test_identity.csv')
        logger.debug(f'📊 [DEBUG] File check: {csv1_path} exists = {os.path.exists(csv1_path)}')
        logger.debug(f'📊 [DEBUG] File check: {csv2_path} exists = {os.path.exists(csv2_path)}')
        
        logger.info('📊 [STREAM] Loading test data...')
        test_trans = pd.read_csv(os.path.join(os.getcwd(), 'content', 'small_test_transaction.csv'))
        test_id = pd.read_csv(os.path.join(os.getcwd(), 'content', 'ieee-fraud-detection', 'test_identity.csv'))
        
        test_trans.columns = test_trans.columns.str.replace('-', '_')
        test_id.columns = test_id.columns.str.replace('-', '_')
        
        logger.info('📊 [STREAM] Merging transaction and identity data...')
        test_merged = test_trans.merge(test_id, on='TransactionID', how='left')
        
        logger.info(f'📊 [STREAM] Will stream {len(test_merged)} predictions')
        logger.info('📊 ' + '=' * 78)
        
        for idx, row in test_merged.iterrows():
            # Check if stream should stop
            stream_info = active_streams.get(visitor_id)
            if not stream_info or stream_info['status'] == 'cleanup':
                logger.warning(f"Stream {visitor_id} stopped early (cleanup requested)")
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
                logger.info(f'📊 [STREAM] Progress for {visitor_id}: {idx + 1}/{len(test_merged)} transactions')
            elif (idx + 1) % 10 == 0:
                logger.info(f'📊 [STREAM] Visitor {visitor_id}: {idx + 1} transactions sent')
        
        logger.info('✅ ' + '=' * 78)
        logger.info(f'✅ [STREAM] Stream complete for visitor {visitor_id}!')
        logger.info(f'✅ [STREAM] Total transactions processed: {len(test_merged)}')
        logger.info('✅ ' + '=' * 78)
        socketio.emit('stream_complete', {
            'total': len(test_merged),
            'message': 'All transactions processed'
        }, room=visitor_id)
        
    except Exception as e:
        logger.error('🔴 ' + '=' * 78)
        logger.error(f'🔴 [STREAM] ERROR in stream for visitor {visitor_id}')
        logger.error(f'🔴 [STREAM] Error: {e}')
        logger.error(f'🔴 [STREAM] Error type: {type(e).__name__}')
        logger.error('🔴 [STREAM] Traceback:')
        logger.exception("Full traceback:")
        logger.error('🔴 ' + '=' * 78)
        socketio.emit('stream_error', {'error': str(e)}, room=visitor_id)
    
    finally:
        if visitor_id in active_streams:
            del active_streams[visitor_id]
            logger.info(f'🧹 [STREAM] Cleaned up stream for {visitor_id}')


if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info('🚀 ' + '=' * 78)
    logger.info('🚀 [STARTUP] Starting Flask-SocketIO server')
    logger.info(f'🚀 [STARTUP] Host: {host}')
    logger.info(f'🚀 [STARTUP] Port: {port}')
    logger.info(f'🚀 [STARTUP] Debug: {debug}')
    logger.info(f'🚀 [STARTUP] HF_REPO_ID: {HF_REPO_ID or "Not set (using local artifacts)"}')
    logger.info('🚀 ' + '=' * 78)

    socketio.run(app, host=host, port=port, debug=debug)
