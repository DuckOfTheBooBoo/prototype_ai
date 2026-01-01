web: gunicorn --chdir . --bind 0.0.0.0:$PORT 'app:socketio' app:app --worker-class eventlet --workers 2 --threads 4
