"""Add game tables for WordleScore ConnectionsScore StrandsScore and Crossword

Revision ID: 109f2d48c31c
Revises: 
Create Date: 2025-05-04 02:25:14.561846

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '109f2d48c31c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create WordleScore table
    op.create_table('wordle_scores',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('word', sa.String(length=5), nullable=False),
                    sa.Column('attempts', sa.Integer(), nullable=False),
                    sa.Column('solved', sa.Boolean(), default=False),
                    sa.Column('date_played', sa.DateTime(), nullable=True),
                    sa.Column('game_state', sa.Text(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create ConnectionsScore table
    op.create_table('connections_scores',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('puzzle_date', sa.DateTime(), nullable=True),
                    sa.Column('solved', sa.Boolean(), default=False),
                    sa.Column('mistakes', sa.Integer(), default=0),
                    sa.Column('time_taken', sa.Integer(), nullable=True),
                    sa.Column('game_state', sa.Text(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create StrandsScore table
    op.create_table('strands_scores',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('puzzle_date', sa.DateTime(), nullable=True),
                    sa.Column('solved', sa.Boolean(), default=False),
                    sa.Column('words_found', sa.Integer(), default=0),
                    sa.Column('time_taken', sa.Integer(), nullable=True),
                    sa.Column('hints_used', sa.Integer(), default=0),
                    sa.Column('game_state', sa.Text(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create CrosswordPuzzle table
    op.create_table('crossword_puzzles',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('puzzle_date', sa.DateTime(), nullable=True),
                    sa.Column('theme', sa.String(length=100), nullable=True),
                    sa.Column('difficulty', sa.String(length=20), nullable=True),
                    sa.Column('grid_size', sa.Integer(), nullable=True),
                    sa.Column('grid_data', sa.Text(), nullable=True),
                    sa.Column('clues_data', sa.Text(), nullable=True),
                    sa.Column('word_count', sa.Integer(), nullable=True),
                    sa.Column('total_letters', sa.Integer(), nullable=True),
                    sa.Column('avg_word_length', sa.Numeric(5, 2), nullable=True),
                    sa.Column('times_played', sa.Integer(), default=0),
                    sa.Column('times_solved', sa.Integer(), default=0),
                    sa.Column('avg_solve_time', sa.Integer(), nullable=True),
                    sa.Column('avg_hints_used', sa.Numeric(5, 2), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('puzzle_date')
                    )

    # Create CrosswordScore table
    op.create_table('crossword_scores',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('puzzle_id', sa.Integer(), nullable=False),
                    sa.Column('puzzle_date', sa.DateTime(), nullable=True),
                    sa.Column('solved', sa.Boolean(), default=False),
                    sa.Column('time_taken', sa.Integer(), nullable=True),
                    sa.Column('hints_used', sa.Integer(), default=0),
                    sa.Column('cells_filled', sa.Integer(), default=0),
                    sa.Column('total_cells', sa.Integer(), default=0),
                    sa.Column('completion_percentage', sa.Numeric(5, 2), nullable=True),
                    sa.Column('game_state', sa.Text(), nullable=True),
                    sa.Column('started_at', sa.DateTime(), nullable=True),
                    sa.Column('completed_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.ForeignKeyConstraint(['puzzle_id'], ['crossword_puzzles.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create CrosswordWordUsage table
    op.create_table('crossword_word_usage',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('word', sa.String(length=20), nullable=True),
                    sa.Column('puzzle_id', sa.Integer(), nullable=True),
                    sa.Column('direction', sa.String(length=6), nullable=True),
                    sa.Column('position_row', sa.Integer(), nullable=True),
                    sa.Column('position_col', sa.Integer(), nullable=True),
                    sa.Column('clue', sa.Text(), nullable=True),
                    sa.Column('times_used', sa.Integer(), default=1),
                    sa.Column('times_guessed_correctly', sa.Integer(), default=0),
                    sa.Column('avg_guess_time', sa.Integer(), nullable=True),
                    sa.Column('difficulty_rating', sa.Numeric(3, 2), nullable=True),
                    sa.ForeignKeyConstraint(['puzzle_id'], ['crossword_puzzles.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create CrosswordHint table
    op.create_table('crossword_hints',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('score_id', sa.Integer(), nullable=False),
                    sa.Column('hint_type', sa.String(length=20), nullable=True),
                    sa.Column('hint_level', sa.Integer(), nullable=True),
                    sa.Column('hint_content', sa.Text(), nullable=True),
                    sa.Column('timestamp', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['score_id'], ['crossword_scores.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes
    op.create_index('idx_user_puzzle', 'crossword_scores', ['user_id', 'puzzle_id'])
    op.create_index('idx_word', 'crossword_word_usage', ['word'])
    op.create_index('idx_puzzle_word', 'crossword_word_usage', ['puzzle_id', 'word'])
    op.create_index('idx_score_hints', 'crossword_hints', ['score_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_score_hints', table_name='crossword_hints')
    op.drop_index('idx_puzzle_word', table_name='crossword_word_usage')
    op.drop_index('idx_word', table_name='crossword_word_usage')
    op.drop_index('idx_user_puzzle', table_name='crossword_scores')

    # Drop tables
    op.drop_table('crossword_hints')
    op.drop_table('crossword_word_usage')
    op.drop_table('crossword_scores')
    op.drop_table('crossword_puzzles')
    op.drop_table('strands_scores')
    op.drop_table('connections_scores')
    op.drop_table('wordle_scores')
