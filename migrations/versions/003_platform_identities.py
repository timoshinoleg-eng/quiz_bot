"""Platform-neutral player identities for MAX and Telegram."""
from alembic import op
import sqlalchemy as sa

revision = "003_platform_identities"
down_revision = "002_v2_catalog_content"
branch_labels = None
depends_on = None


def upgrade():
    # Revision 002 deliberately calls Base.metadata.create_all for SQLite bootstrap.
    # On a fresh install with the current metadata it has already made this table.
    if "platform_identities" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "platform_identities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("external_user_id", sa.String(64), nullable=False),
        sa.Column("username", sa.String(255)), sa.Column("first_name", sa.String(255)), sa.Column("last_name", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "external_user_id", name="uq_platform_external_user"),
    )
    op.create_index("ix_platform_identities_user_id", "platform_identities", ["user_id"])
    op.create_index("ix_platform_identities_platform", "platform_identities", ["platform"])


def downgrade():
    op.drop_table("platform_identities")
