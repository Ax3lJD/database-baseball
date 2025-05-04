from flask import Flask
from flask_login import LoginManager
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

Base = declarative_base()

app = Flask(__name__)
app.config.from_object(Config)

# SQLAlchemy setup with connection pooling
engine = create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Import models after Base is created
from app.models import User, TriviaScore, WordleScore, ConnectionsScore, StrandsScore
Base.metadata.create_all(engine)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()

@login_manager.user_loader
def load_user(user_id):
    with Session() as session:
        user = session.query(User).get(int(user_id))
        if user:
            session.expunge(user)
        return user

@app.template_filter('format_time')
def format_time(seconds):
    """Format seconds into MM:SS format"""
    if not seconds:
        return "N/A"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"

from app import routes