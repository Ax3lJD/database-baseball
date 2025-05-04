from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app import Base
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime, Text
from sqlalchemy.orm import relationship
from app import Base
from flask_login import UserMixin
from datetime import datetime

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    scores = relationship("TriviaScore", back_populates="user")
    wordle_scores = relationship("WordleScore", back_populates="user")
    connections_scores = relationship("ConnectionsScore", back_populates="user")
    strands_scores = relationship("StrandsScore", back_populates="user")


class TriviaScore(Base):
    __tablename__ = 'trivia_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    score = Column(Integer, default=0, nullable=False)  # Total correct answers
    total_attempted = Column(Integer, default=0, nullable=False)  # Total number of questions attempted
    correct_answers = Column(Integer, default=0)  # New column to track correct answers
    percentage = Column(Numeric(5, 2), default=0.00)
    round_number = Column(Integer, default=1)  # New column to track round number

    user = relationship("User", back_populates="scores")


class WordleScore(Base):
    __tablename__ = 'wordle_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False)
    solved = Column(Boolean, default=False)
    date_played = Column(DateTime, default=datetime.utcnow)
    game_state = Column(Text)  # JSON string to store game state

    user = relationship("User", back_populates="wordle_scores")


class ConnectionsScore(Base):
    __tablename__ = 'connections_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    puzzle_date = Column(DateTime, default=datetime.utcnow)
    solved = Column(Boolean, default=False)
    mistakes = Column(Integer, default=0)
    time_taken = Column(Integer)  # seconds
    game_state = Column(Text)  # JSON string

    user = relationship("User", back_populates="connections_scores")


class StrandsScore(Base):
    __tablename__ = 'strands_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    puzzle_date = Column(DateTime, default=datetime.utcnow)
    solved = Column(Boolean, default=False)
    words_found = Column(Integer, default=0)
    time_taken = Column(Integer)
    game_state = Column(Text)

    user = relationship("User", back_populates="strands_scores")