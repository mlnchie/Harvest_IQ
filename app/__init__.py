import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_socketio import SocketIO
from flask_migrate import Migrate
from sqlalchemy import text
from config.development import DevelopmentConfig

# ─────────────────────────────────────────────
# EXTENSIONS
# ─────────────────────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
socketio = SocketIO(async_mode="threading")
migrate = Migrate()

# ─────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────
def create_app(config=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config)

    # 🛠️ DYNAMIC DATABASE CONFIG FOR DEPLOYMENT
    # Kukunin ang DATABASE_URL mula sa Render Environment Variables
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # SQLAlchemy 1.4+ fix: Dapat 'postgresql://' ang simula, hindi 'postgres://'
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    # 🔐 PRODUCTION SECRET KEY
    if os.environ.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

    # INIT EXTENSIONS
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # ─────────────────────────────────────────
    # SQLITE WAL MODE (ONLY IF USING SQLITE)
    # ─────────────────────────────────────────
    with app.app_context():
        # I-run lang ang PRAGMA kung SQLite ang gamit para hindi mag-error sa Postgres
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            db.session.execute(text("PRAGMA journal_mode=WAL;"))
            db.session.commit()

    # LOGIN SETTINGS
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # USER LOADER
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ─────────────────────────────────────────
    # REGISTER BLUEPRINTS
    # ─────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    from app.routes.orders import orders_bp
    from app.routes.users import users_bp
    from app.routes.admin import admin_bp
    from app.routes.search import search_bp
    from app.routes.cart import cart_bp
    from app.routes.payment import payment_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(search_bp, url_prefix="/search")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(payment_bp, url_prefix="/payment")
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # ─────────────────────────────────────────
    # AUTO CREATE DATABASE
    # ─────────────────────────────────────────
    with app.app_context():
        db.create_all()
        from app.utils.helpers import seed_categories, seed_admin
        seed_categories()
        seed_admin()

    return app