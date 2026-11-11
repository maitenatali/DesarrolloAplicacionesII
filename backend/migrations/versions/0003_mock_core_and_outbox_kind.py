"""outbox_event.kind (EVENT | NOTIFICATION) + tables of the local CORE simulator

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
alter table outbox_event add column kind varchar(15) not null default 'EVENT';
alter table outbox_event add constraint outbox_event_kind_ck check (kind in ('EVENT','NOTIFICATION'));

create table mock_core_signing_key (
  kid         varchar(64) primary key,
  private_pem text        not null,
  created_at  timestamptz not null default now()
);

create table mock_core_user (
  id            varchar(36)  primary key,
  email         varchar(150) not null unique,
  password_hash varchar(255) not null,
  first_name    varchar(80)  not null,
  last_name     varchar(80)  not null,
  roles         jsonb        not null,
  permissions   jsonb        not null,
  career_ids    jsonb        not null,
  status        varchar(15)  not null default 'ACTIVE',
  created_at    timestamptz  not null default now(),
  constraint mock_core_user_status_ck check (status in ('INVITED','ACTIVE','SUSPENDED','DISABLED'))
);

create table mock_core_session (
  jti        varchar(36) primary key,
  user_id    varchar(36) not null,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create table mock_core_wallet_tx (
  id                 varchar(36)   primary key,
  user_id            varchar(36)   not null,
  status             varchar(10)   not null,
  type               varchar(10)   not null,
  concept            varchar(30)   not null,
  amount             numeric(14,2) not null,
  currency           varchar(3)    not null default 'ARS',
  balance_after      numeric(14,2) not null,
  source_module      varchar(30)   not null,
  external_reference varchar(150)  not null,
  description        varchar(255),
  idempotency_key    varchar(64),
  request_hash       varchar(64),
  created_at         timestamptz   not null default now(),
  constraint mock_core_wallet_tx_idem_uk unique (user_id, idempotency_key),
  constraint mock_core_wallet_tx_type_ck check (type in ('CREDIT','DEBIT','REVERSAL'))
);
create index mock_core_wallet_tx_user_idx on mock_core_wallet_tx (user_id, created_at);

create table mock_core_notification (
  id               varchar(36)  primary key,
  user_id          varchar(36)  not null,
  type             varchar(60)  not null,
  title            varchar(200) not null,
  message          text         not null,
  action_url       varchar(300),
  source_module    varchar(30)  not null,
  source_reference varchar(200) not null,
  read             boolean      not null default false,
  read_at          timestamptz,
  expires_at       timestamptz,
  created_at       timestamptz  not null default now(),
  constraint mock_core_notification_source_uk unique (user_id, type, source_module, source_reference)
);
create index mock_core_notification_user_idx on mock_core_notification (user_id, created_at);

alter table mock_core_signing_key  enable row level security;
alter table mock_core_user         enable row level security;
alter table mock_core_session      enable row level security;
alter table mock_core_wallet_tx    enable row level security;
alter table mock_core_notification enable row level security;
"""
    )


def downgrade() -> None:
    op.execute(
        """
drop table if exists mock_core_notification;
drop table if exists mock_core_wallet_tx;
drop table if exists mock_core_session;
drop table if exists mock_core_user;
drop table if exists mock_core_signing_key;
alter table outbox_event drop constraint if exists outbox_event_kind_ck;
alter table outbox_event drop column if exists kind;
"""
    )
