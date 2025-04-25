from flask import Flask
from flask_login import LoginManager
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

app = Flask(__name__)
app.config.from_object(Config)

# SQLAlchemy setup
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)

from app import models
Base.metadata.create_all(engine)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
from app.models import User
from app import Session

@login_manager.user_loader
def load_user(user_id):
    session = Session()
    try:
        return session.query(User).get(int(user_id))
    finally:
        session.close()


from app import routes