from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app import Base
from flask_login import UserMixin


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    scores = relationship("TriviaScore", back_populates="user")


class TriviaScore(Base):
    __tablename__ = 'trivia_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    score = Column(Integer, default=0, nullable=False)
    total_attempted = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0)
    percentage = Column(Numeric(5, 2), default=0.00)
    round_number = Column(Integer, default=1)

    user = relationship("User", back_populates="scores")


class People(Base):
    __tablename__ = 'people'

    playerID = Column('playerid', String(20), primary_key=True)
    nameFirst = Column('namefirst', String(50))
    nameLast = Column('namelast', String(50))


class Batting(Base):
    __tablename__ = 'batting'

    id = Column(Integer, primary_key=True, autoincrement=True)
    playerID = Column('playerid', String(20))
    yearID = Column('yearid', Integer)
    b_HR = Column('b_hr', Integer)
    b_AB = Column('b_ab', Integer)
    b_RBI = Column('b_rbi', Integer)


class Teams(Base):
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_name = Column('team_name', String(100))
    yearID = Column('yearid', Integer)
    team_W = Column('team_w', Integer)
