"""Install a device-scoped, transactional Supabase RPC on PostgreSQL."""
from pathlib import Path
from alembic import op

revision = "0002_sensor_rpc"
down_revision = "a9b6f621d0dc"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        sql = Path(__file__).resolve().parents[2] / "database" / "sensor_rpc.sql"
        op.get_bind().exec_driver_sql(sql.read_text(encoding="utf-8"))


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS public.sync_spot(boolean)")
        # Keep RLS enabled on downgrade: never reopen client access implicitly.
