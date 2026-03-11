import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # Use DATABASE_URL env var (set by Railway), fallback to local MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        try:
            from csi3335f2024 import mysql
            SQLALCHEMY_DATABASE_URI = (
                f"mysql+pymysql://{mysql['user']}:{mysql['password']}@{mysql['host']}/{mysql['database']}"
                "?charset=utf8mb4"
            )
        except ImportError:
            SQLALCHEMY_DATABASE_URI = 'sqlite:///trivia.db'

    # Railway PostgreSQL uses postgres:// but SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 1800
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
