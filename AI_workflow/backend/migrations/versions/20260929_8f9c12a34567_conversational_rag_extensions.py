"""conversational rag extensions

Add conversation_id, entities, pending_state to chat_queries and support clarification answer_type.

Revision ID: 8f9c12a34567
Revises: 5e5b633f0a14
Create Date: 2026-09-29 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f9c12a34567'
down_revision: Union[str, Sequence[str], None] = '634874d3070d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_queries', sa.Column('conversation_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.add_column('chat_queries', sa.Column('entities', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('chat_queries', sa.Column('pending_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    op.create_index('ix_chat_queries_conversation_id_created_at', 'chat_queries', ['conversation_id', 'created_at'], unique=False)
    op.create_index('ix_chat_queries_user_id_conversation_id', 'chat_queries', ['user_id', 'conversation_id'], unique=False)
    
    # Update check constraint safely
    op.execute("ALTER TABLE chat_queries DROP CONSTRAINT IF EXISTS ck_chat_queries_answer_type;")
    op.create_check_constraint(
        'ck_chat_queries_answer_type',
        'chat_queries',
        "answer_type IN ('answered', 'fallback', 'abstained', 'unsupported', 'clarification')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_chat_queries_answer_type', 'chat_queries', type_='check')
    op.create_check_constraint(
        'ck_chat_queries_answer_type',
        'chat_queries',
        "answer_type IN ('answered', 'fallback', 'abstained', 'unsupported')"
    )
    op.drop_index('ix_chat_queries_user_id_conversation_id', table_name='chat_queries')
    op.drop_index('ix_chat_queries_conversation_id_created_at', table_name='chat_queries')
    op.drop_column('chat_queries', 'pending_state')
    op.drop_column('chat_queries', 'entities')
    op.drop_column('chat_queries', 'conversation_id')
