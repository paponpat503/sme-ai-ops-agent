"""Create tenant-scoped business tables."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("customers", sa.Column("tenant_id", sa.String(80), primary_key=True), sa.Column("customer_id", sa.String(40), primary_key=True), sa.Column("customer_name", sa.String(200), nullable=False), sa.Column("industry", sa.String(120), nullable=False), sa.Column("plan", sa.String(80), nullable=False), sa.Column("owner", sa.String(120), nullable=False), sa.Column("health_score", sa.Integer(), nullable=False))
    op.create_table("tickets", sa.Column("tenant_id", sa.String(80), primary_key=True), sa.Column("ticket_id", sa.String(40), primary_key=True), sa.Column("customer_id", sa.String(40), nullable=False, index=True), sa.Column("status", sa.String(40), nullable=False), sa.Column("priority", sa.String(40), nullable=False), sa.Column("days_open", sa.Integer(), nullable=False), sa.Column("issue", sa.Text(), nullable=False))
    op.create_table("orders", sa.Column("tenant_id", sa.String(80), primary_key=True), sa.Column("order_id", sa.String(40), primary_key=True), sa.Column("customer_id", sa.String(40), nullable=False, index=True), sa.Column("amount_usd", sa.Float(), nullable=False), sa.Column("payment_status", sa.String(40), nullable=False), sa.Column("due_date", sa.String(20), nullable=False))
    op.create_table("crm_notes", sa.Column("tenant_id", sa.String(80), primary_key=True), sa.Column("note_id", sa.String(40), primary_key=True), sa.Column("customer_id", sa.String(40), nullable=False, index=True), sa.Column("date", sa.String(20), nullable=False), sa.Column("note", sa.Text(), nullable=False))
    op.create_table("crm_tasks", sa.Column("tenant_id", sa.String(80), primary_key=True), sa.Column("task_id", sa.String(40), primary_key=True), sa.Column("customer_id", sa.String(40), nullable=False, index=True), sa.Column("task", sa.Text(), nullable=False), sa.Column("due_date", sa.String(20), nullable=False), sa.Column("owner", sa.String(120), nullable=False), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_task_tenant_idempotency"))


def downgrade() -> None:
    op.drop_table("crm_tasks")
    op.drop_table("crm_notes")
    op.drop_table("orders")
    op.drop_table("tickets")
    op.drop_table("customers")
