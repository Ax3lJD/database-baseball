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
    crossword_scores = relationship("CrosswordScore", back_populates="user")


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
    hints_used = Column(Integer, default=0)  # Add this field
    game_state = Column(Text)

    user = relationship("User", back_populates="strands_scores")


class CrosswordPuzzle(Base):
    __tablename__ = 'crossword_puzzles'

    id = Column(Integer, primary_key=True)
    puzzle_date = Column(DateTime, default=datetime.utcnow, unique=True)
    theme = Column(String(100))
    difficulty = Column(String(20))
    grid_size = Column(Integer)
    grid_data = Column(Text)  # JSON of the grid
    clues_data = Column(Text)  # JSON of clues
    word_count = Column(Integer)
    total_letters = Column(Integer)
    avg_word_length = Column(Numeric(5, 2))
    times_played = Column(Integer, default=0)
    times_solved = Column(Integer, default=0)
    avg_solve_time = Column(Integer)  # seconds
    avg_hints_used = Column(Numeric(5, 2))

    scores = relationship("CrosswordScore", back_populates="puzzle")


class CrosswordScore(Base):
    __tablename__ = 'crossword_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    puzzle_id = Column(Integer, ForeignKey('crossword_puzzles.id'), nullable=False)
    puzzle_date = Column(DateTime, default=datetime.utcnow)
    solved = Column(Boolean, default=False)
    time_taken = Column(Integer)  # seconds
    hints_used = Column(Integer, default=0)
    cells_filled = Column(Integer, default=0)
    total_cells = Column(Integer, default=0)
    completion_percentage = Column(Numeric(5, 2))
    game_state = Column(Text)  # JSON of the game state
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="crossword_scores")
    puzzle = relationship("CrosswordPuzzle", back_populates="scores")


class CrosswordWordUsage(Base):
    __tablename__ = 'crossword_word_usage'

    id = Column(Integer, primary_key=True)
    word = Column(String(20), index=True)
    puzzle_id = Column(Integer, ForeignKey('crossword_puzzles.id'))
    direction = Column(String(6))  # across or down
    position_row = Column(Integer)
    position_col = Column(Integer)
    clue = Column(Text)
    times_used = Column(Integer, default=1)
    times_guessed_correctly = Column(Integer, default=0)
    avg_guess_time = Column(Integer)  # seconds
    difficulty_rating = Column(Numeric(3, 2))  # 0-1 scale

    puzzle = relationship("CrosswordPuzzle")


class CrosswordHint(Base):
    __tablename__ = 'crossword_hints'

    id = Column(Integer, primary_key=True)
    score_id = Column(Integer, ForeignKey('crossword_scores.id'))
    hint_type = Column(String(20))  # letter, word, statistical
    hint_level = Column(Integer)
    hint_content = Column(Text)  # JSON of hint details
    timestamp = Column(DateTime, default=datetime.utcnow)

    score = relationship("CrosswordScore")