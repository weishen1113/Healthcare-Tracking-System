from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        email = current_user.email
        print(f"[SocketIO] User connected: {email}")
        emit('user_connected', {'email': email})
    else:
        print("[SocketIO] Unauthorized connection attempt.")
        emit('unauthorized')
        return False  # Disconnect unauthorized users

@socketio.on('login_event')
def handle_login_event(data):
    if current_user.is_authenticated:
        email = current_user.email
        print(f"[SocketIO] Login event from: {email}")
        emit('login_broadcast', {
            'email': email,
            'message': 'logged in successfully'
        }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        print(f"[SocketIO] User disconnected: {current_user.email}")
    else:
        print("[SocketIO] Unauthenticated user disconnected.")
