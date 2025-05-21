import os
import logging
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from db import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))

# Set up CSRF protection
csrf = CSRFProtect(app)

# Configure proxy settings for proper URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration - Use PostgreSQL for production
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/bookquiz"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Test connections before using them
    "pool_size": 10,  # Maximum number of connections to keep
    "max_overflow": 20,  # Maximum number of connections to create beyond pool_size
}

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# Set login view to string
login_manager.login_view = 'auth.login'  # type: ignore
login_manager.login_message_category = 'info'

# Import routes
from routes import main as main_routes
from auth import auth as auth_routes
from quiz import quiz as quiz_routes
from admin import admin as admin_routes

# Register blueprints
app.register_blueprint(main_routes)
app.register_blueprint(auth_routes, url_prefix='/auth')
app.register_blueprint(quiz_routes, url_prefix='/quiz')
app.register_blueprint(admin_routes, url_prefix='/admin')

# Import user loader
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    
    # Create indexes for optimal query performance
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        from sqlalchemy import text
        try:
            # Create index on user email and username for fast lookups
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_email ON "user" (email)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_username ON "user" (username)'))
            
            # Create index on quiz fields that are frequently queried
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_quiz_user_id ON quiz (user_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_quiz_is_completed ON quiz (is_completed)'))
            
            # Create index on shared content
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_shared_content_share_key ON shared_content (share_key)'))
            
            db.session.commit()
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {str(e)}")
            db.session.rollback()
