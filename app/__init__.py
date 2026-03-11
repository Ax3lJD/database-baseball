from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import QueuePool
import logging
from sqlalchemy import event
from sqlalchemy.pool import Pool

Base = declarative_base()

app = Flask(__name__)
app.config.from_object(Config)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@event.listens_for(Pool, "connect")
def connect(dbapi_conn, connection_record):
    logger.info('Database connection created')

@event.listens_for(Pool, "checkout")
def checkout(dbapi_conn, connection_record, connection_proxy):
    logger.info('Connection checked out from pool')

@event.listens_for(Pool, "checkin")
def checkin(dbapi_conn, connection_record):
    logger.info('Connection returned to pool')

@event.listens_for(engine, "close")
def close(dbapi_conn, connection_record):
    logger.info('Database connection closed')

@event.listens_for(engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params, execution_options):
    try:
        logger.debug(f"Query: {clauseelement}")
        logger.debug(f"Params: {params}")
    except Exception as e:
        logger.debug(f"Query: {type(clauseelement).__name__} (unable to render)")
        logger.debug(f"Params: {params}")

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Import all models after Base is created
from app.models import (
    User,
    TriviaScore,
    WordleScore,
    ConnectionsScore,
    StrandsScore,
    CrosswordPuzzle,
    CrosswordScore,
    CrosswordWordUsage,
    CrosswordHint
)

migrate = Migrate()

class MockDB:
    def __init__(self, metadata):
        self.metadata = metadata
        self.engine = engine

migrate.init_app(app, db=MockDB(Base.metadata), render_as_batch=True)

Base.metadata.create_all(engine)

# Auto-seed baseball data on first run
from seed import seed_database
seed_database(engine)

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
