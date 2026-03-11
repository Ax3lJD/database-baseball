import os
from csi3335f2024 import mysql

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{mysql['user']}:{mysql['password']}@{mysql['host']}/{mysql['database']}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 1800
    DEBUG = True