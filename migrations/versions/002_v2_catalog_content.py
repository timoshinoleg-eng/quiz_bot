"""Quiz Battle V2 catalog and player-content history."""
from alembic import op
import sqlalchemy as sa
from models import Base
revision="002_v2_catalog_content"; down_revision="001"; branch_labels=None; depends_on=None
def upgrade():
    bind=op.get_bind(); Base.metadata.create_all(bind=bind)
    # SQLite/PostgreSQL compatibility for the original beta Questions table.
    existing={column["name"] for column in sa.inspect(bind).get_columns("questions")}
    columns=[sa.Column("source_url",sa.String(500),nullable=True),sa.Column("source_license",sa.String(120),nullable=False,server_default="CC0-1.0"),sa.Column("language",sa.String(8),nullable=False,server_default="ru"),sa.Column("tags",sa.JSON(),nullable=False,server_default="[]"),sa.Column("age_min",sa.Integer(),nullable=False,server_default="10"),sa.Column("age_max",sa.Integer(),nullable=False,server_default="14"),sa.Column("verified",sa.Boolean(),nullable=False,server_default="0"),sa.Column("content_rating",sa.String(16),nullable=False,server_default="kids")]
    with op.batch_alter_table("questions") as batch:
        for column in columns:
            if column.name not in existing: batch.add_column(column)
def downgrade(): pass
