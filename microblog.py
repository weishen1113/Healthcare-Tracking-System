from dotenv import load_dotenv
import os
load_dotenv()

from flask_migrate import Migrate
from app import socketio, create_app, db
from app.config import DeploymentConfig

# Make these available globally for Flask CLI
application = create_app(DeploymentConfig)
migrate = Migrate(application, db)

# Run with SocketIO if script is executed directly
if __name__ == '__main__':
    socketio.run(application, debug=True)

