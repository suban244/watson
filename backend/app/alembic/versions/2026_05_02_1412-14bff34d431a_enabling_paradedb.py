"""Enabling ParadeDB

Revision ID: 14bff34d431a
Revises: d7a464a3187e
Create Date: 2026-05-02 14:12:52.108407

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "14bff34d431a"
down_revision: str | None = "d7a464a3187e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop BM25 indexes owned by pg_textsearch before swapping the extension
    op.drop_index("ix_transaction_description_bm25", table_name="transactions")
    op.drop_index("ix_transaction_title_bm25", table_name="transactions")

    # Drop pg_textsearch — this releases ownership of the bm25 access method
    op.execute("DROP EXTENSION IF EXISTS pg_textsearch CASCADE")

    # Install pg_search (ParadeDB), which registers its own bm25 access method
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_bm25", table_name="transactions")

    op.execute("DROP EXTENSION IF EXISTS pg_search CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_textsearch")

    op.execute(
        "CREATE INDEX ix_transaction_title_bm25 ON transactions"
        " USING bm25 (title) WITH (text_config = 'english')"
    )
    op.execute(
        "CREATE INDEX ix_transaction_description_bm25 ON transactions"
        " USING bm25 (description) WITH (text_config = 'english')"
    )
