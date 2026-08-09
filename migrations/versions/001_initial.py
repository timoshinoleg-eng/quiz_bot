"""Initial beta schema.

This repository is still in closed beta, so the first migration is the
canonical schema rather than a compatibility layer for the pre-beta MVP.
The SQLAlchemy metadata is deliberately shared with runtime table creation;
that keeps SQLite development and PostgreSQL deployment aligned.
"""

from typing import Sequence, Union

from alembic import op

from models import Base

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
