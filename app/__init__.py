from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(config_class='config.Config'):
    """Creates and configures an instance of the Flask application."""
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        # Import parts of our application
        from . import models # Import models to register them with SQLAlchemy
        from .routes import main_bp

        # Register Blueprints
        app.register_blueprint(main_bp)

        return app