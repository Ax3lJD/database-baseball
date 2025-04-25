from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app import Base
from flask_login import UserMixin

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    scores = relationship("TriviaScore", back_populates="user")


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
