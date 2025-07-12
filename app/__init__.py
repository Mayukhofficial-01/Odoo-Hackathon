from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_migrate import Migrate

# Initialize extensions (no app passed here yet)
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
migrate = Migrate()  # 👈 You missed this earlier

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'stackit-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stackit.db'

    # Email config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'stackitteam@gmail.com'
    app.config['MAIL_PASSWORD'] = 'jdea cgue tils mjvn'  # App password only

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)  # 👈 Register Flask-Migrate here

    from app.routes import register_routes
    register_routes(app)

    return app
