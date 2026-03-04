"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    difficulty_level = postgresql.ENUM('easy', 'medium', 'hard', name='difficultylevel')
    difficulty_level.create(op.get_bind())
    
    question_category = postgresql.ENUM('history', 'science', 'art', 'sports', 'geography', 'entertainment', 'general', name='questioncategory')
    question_category.create(op.get_bind())
    
    game_status = postgresql.ENUM('in_progress', 'completed', 'abandoned', name='gamestatus')
    game_status.create(op.get_bind())
    
    duel_status = postgresql.ENUM('waiting', 'in_progress', 'completed', 'expired', name='duelstatus')
    duel_status.create(op.get_bind())
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('score_total', sa.Integer(), server_default='0', nullable=True),
        sa.Column('games_played', sa.Integer(), server_default='0', nullable=True),
        sa.Column('games_won', sa.Integer(), server_default='0', nullable=True),
        sa.Column('current_state', sa.String(length=50), nullable=True),
        sa.Column('state_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('premium_until', sa.DateTime(), nullable=True),
        sa.Column('daily_streak', sa.Integer(), server_default='0', nullable=True),
        sa.Column('last_played', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('history', 'science', 'art', 'sports', 'geography', 'entertainment', 'general', name='questioncategory'), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficultylevel'), nullable=False),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('wrong_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('usage_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('correct_rate', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Games table
    op.create_table(
        'games',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('category', sa.Enum('history', 'science', 'art', 'sports', 'geography', 'entertainment', 'general', name='questioncategory'), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficultylevel'), nullable=False),
        sa.Column('question_count', sa.Integer(), server_default='10', nullable=True),
        sa.Column('status', sa.Enum('in_progress', 'completed', 'abandoned', name='gamestatus'), server_default='in_progress', nullable=True),
        sa.Column('current_question_index', sa.Integer(), server_default='0', nullable=True),
        sa.Column('score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('correct_answers', sa.Integer(), server_default='0', nullable=True),
        sa.Column('lives_remaining', sa.Integer(), server_default='3', nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Game questions table
    op.create_table(
        'game_questions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.BigInteger(), nullable=False),
        sa.Column('question_id', sa.BigInteger(), nullable=False),
        sa.Column('was_answered', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('user_answer', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('answer_time', sa.Float(), nullable=True),
        sa.Column('points_earned', sa.Integer(), server_default='0', nullable=True),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Duels table
    op.create_table(
        'duels',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('player1_id', sa.BigInteger(), nullable=False),
        sa.Column('player2_id', sa.BigInteger(), nullable=True),
        sa.Column('category', sa.Enum('history', 'science', 'art', 'sports', 'geography', 'entertainment', 'general', name='questioncategory'), nullable=False),
        sa.Column('question_count', sa.Integer(), server_default='5', nullable=True),
        sa.Column('status', sa.Enum('waiting', 'in_progress', 'completed', 'expired', name='duelstatus'), server_default='waiting', nullable=True),
        sa.Column('player1_score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('player2_score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('player1_correct', sa.Integer(), server_default='0', nullable=True),
        sa.Column('player2_correct', sa.Integer(), server_default='0', nullable=True),
        sa.Column('winner_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['player1_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['player2_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='RUB', nullable=True),
        sa.Column('provider', sa.String(length=50), server_default='yookassa', nullable=True),
        sa.Column('provider_payment_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('subscription_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Analytics events table
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Daily streaks table
    op.create_table(
        'daily_streaks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('streak_date', sa.DateTime(), nullable=False),
        sa.Column('streak_count', sa.Integer(), server_default='1', nullable=True),
        sa.Column('reward_claimed', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_questions_category', 'questions', ['category'])
    op.create_index('ix_questions_difficulty', 'questions', ['difficulty'])
    op.create_index('ix_questions_is_active', 'questions', ['is_active'])
    op.create_index('ix_games_user_id', 'games', ['user_id'])
    op.create_index('ix_games_status', 'games', ['status'])
    op.create_index('ix_game_questions_game_id', 'game_questions', ['game_id'])
    op.create_index('ix_duels_status', 'duels', ['status'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('ix_analytics_events_event_type', 'analytics_events', ['event_type'])
    op.create_index('ix_analytics_events_created_at', 'analytics_events', ['created_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('daily_streaks')
    op.drop_table('analytics_events')
    op.drop_table('payments')
    op.drop_table('duels')
    op.drop_table('game_questions')
    op.drop_table('games')
    op.drop_table('questions')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS duelstatus')
    op.execute('DROP TYPE IF EXISTS gamestatus')
    op.execute('DROP TYPE IF EXISTS questioncategory')
    op.execute('DROP TYPE IF EXISTS difficultylevel')
