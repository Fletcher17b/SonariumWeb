import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_mail import Mail
from flask_bcrypt import Bcrypt

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    bcrypt.init_app(app)
    

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = 'mariobgrillo.workmail@gmail.com'
   


    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app,db)
    
    from .routes import app as routes_blueprint
    app.register_blueprint(routes_blueprint)

    with app.app_context():
        from . import routes
        from .models import User

    return app

