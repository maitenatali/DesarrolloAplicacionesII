"""outbox_event (transactional outbox)

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
create table outbox_event (
  id              uuid primary key,
  event_type      varchar(100) not null,
  subject         varchar(200) not null,
  payload         jsonb        not null,
  status          varchar(10)  not null default 'PENDING',
  attempts        integer      not null default 0,
  next_attempt_at timestamptz  not null default now(),
  last_error      text,
  created_at      timestamptz  not null default now(),
  sent_at         timestamptz,
  constraint outbox_event_status_ck check (status in ('PENDING','SENT','FAILED'))
);
create index outbox_event_due_idx on outbox_event (next_attempt_at) where status = 'PENDING';
alter table outbox_event enable row level security;
"""
    )


def downgrade() -> None:
    op.execute("drop table if exists outbox_event;")
