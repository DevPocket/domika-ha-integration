"""
Added temporary event table.

Revision ID: 9291d34e8062
Revises: b74951a1e96b
Create Date: 2024-05-12 14:44:29.246644
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9291d34e8062'
down_revision: Union[str, None] = 'b74951a1e96b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade step."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'events',
        sa.Column('event_id', sa.Uuid(), nullable=False),
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
        sa.PrimaryKeyConstraint('event_id', 'entity_id', 'attribute', name=op.f('pk_events')),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade step."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('events')
    # ### end Alembic commands ###