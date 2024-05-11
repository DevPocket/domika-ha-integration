"""
Initial revision.

Revision ID: 4c09d7fe055a
Revises:
Create Date: 2024-05-08 21:08:54.747514
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4c09d7fe055a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade step."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'dashboards',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('dashboard', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', name=op.f('pk_dashboards')),
    )
    op.create_table(
        'devices',
        sa.Column('app_session_id', sa.String(), nullable=False),
        sa.Column('push_session_id', sa.Uuid(), nullable=True),
        sa.Column('push_token', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column(
            'last_update',
            sa.Integer(),
            server_default=sa.text("(datetime('now'))"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('app_session_id', name=op.f('pk_devices')),
    )
    op.create_table(
        'push_data',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('app_session_id', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('attribute', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('context_id', sa.String(), nullable=False),
        sa.Column(
            'timestamp',
            sa.Integer(),
            server_default=sa.text("(datetime('now'))"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['app_session_id'],
            ['devices.app_session_id'],
            name=op.f('fk_push_data_app_session_id_devices'),
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_push_data')),
        sa.UniqueConstraint(
            'app_session_id',
            'entity_id',
            'attribute',
            name=op.f('uq_push_data_app_session_id'),
        ),
    )
    op.create_table(
        'subscriptions',
        sa.Column('app_session_id', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('attribute', sa.String(), nullable=False),
        sa.Column('need_push', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['app_session_id'],
            ['devices.app_session_id'],
            name=op.f('fk_subscriptions_app_session_id_devices'),
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'app_session_id',
            'entity_id',
            'attribute',
            name=op.f('pk_subscriptions'),
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade step."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('subscriptions')
    op.drop_table('push_data')
    op.drop_table('devices')
    op.drop_table('dashboards')
    # ### end Alembic commands ###
