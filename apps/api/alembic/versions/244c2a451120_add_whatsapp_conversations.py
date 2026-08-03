"""add whatsapp conversations

Revision ID: 244c2a451120
Revises: b9fbabb5769a
Create Date: 2026-07-30 10:49:45.072826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '244c2a451120'
down_revision: Union[str, None] = 'b9fbabb5769a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('whatsapp_conversations',
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('lead_id', sa.UUID(), nullable=True),
    sa.Column('wa_phone', sa.String(length=32), nullable=False, comment="E.164 without '+', as Meta sends it"),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('last_inbound_at', sa.DateTime(timezone=True), nullable=True, comment='Start of the 24-hour free-form window. Null means never messaged us.'),
    sa.Column('ai_enabled', sa.Boolean(), nullable=False, comment='Turned off automatically once a human takes over, so the AI stops talking over them.'),
    sa.Column('handed_off_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_whatsapp_conversations_lead_id'), 'whatsapp_conversations', ['lead_id'], unique=False)
    op.create_index('uq_whatsapp_owner_phone', 'whatsapp_conversations', ['owner_id', 'wa_phone'], unique=True)
    op.create_table('whatsapp_messages',
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('direction', sa.Enum('INBOUND', 'OUTBOUND', name='wa_direction'), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'SENT', 'FAILED', 'RECEIVED', name='wa_message_status'), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('external_id', sa.String(length=255), nullable=True, comment="Meta's message id, used to ignore redelivered webhooks"),
    sa.Column('is_ai_generated', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['whatsapp_conversations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_whatsapp_messages_conversation_id'), 'whatsapp_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_external_id'), 'whatsapp_messages', ['external_id'], unique=False)
    op.add_column('automation_settings', sa.Column('whatsapp_ai_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('automation_settings', 'whatsapp_ai_enabled')
    for enum_name in ('wa_message_status', 'wa_direction'):
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
    op.drop_index(op.f('ix_whatsapp_messages_external_id'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_conversation_id'), table_name='whatsapp_messages')
    op.drop_table('whatsapp_messages')
    op.drop_index('uq_whatsapp_owner_phone', table_name='whatsapp_conversations')
    op.drop_index(op.f('ix_whatsapp_conversations_lead_id'), table_name='whatsapp_conversations')
    op.drop_table('whatsapp_conversations')
