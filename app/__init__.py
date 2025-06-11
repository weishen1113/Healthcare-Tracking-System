import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_socketio import SocketIO
from dotenv import load_dotenv
from app.config import Config
from app.config import DeploymentConfig

# Load environment variables
load_dotenv()

# Unbound Flask extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")



def create_app(config=DeploymentConfig):
    application = Flask(__name__, instance_relative_config=True)

    # Load config
    application.config.from_object(config)

    from app.blueprints import blueprint
    application.register_blueprint(blueprint)

    # Initialize extensions
    db.init_app(application)
    migrate.init_app(application, db)
    csrf.init_app(application)
    login.init_app(application)
    login.login_view = 'main.login'
    socketio.init_app(application)

    # Import routes, models, sockets
    from app import routes, models, sockets

    return application
