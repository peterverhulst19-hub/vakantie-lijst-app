-- Eenmalig uitvoeren in Supabase's SQL Editor (Dashboard -> SQL Editor -> New query).

create table if not exists users (
    id            bigserial primary key,
    email         text not null unique,
    display_name  text,
    created_at    timestamptz not null default now()
);

create table if not exists groups (
    id             bigserial primary key,
    name           text not null,
    owner_user_id  bigint not null references users(id) on delete cascade,
    invite_code    text not null unique,
    created_at     timestamptz not null default now()
);

create table if not exists group_members (
    id         bigserial primary key,
    group_id   bigint not null references groups(id) on delete cascade,
    user_id    bigint not null references users(id) on delete cascade,
    joined_at  timestamptz not null default now(),
    unique (group_id, user_id)
);

create table if not exists items (
    id                bigserial primary key,
    group_id          bigint not null references groups(id) on delete cascade,
    object            text not null,
    aantal            integer not null default 1,
    type              text not null default 'Overig',
    aangevinkt        smallint not null default 0 check (aangevinkt in (0, 1)),
    person_user_id    bigint references users(id) on delete cascade,
    added_by_user_id  bigint references users(id) on delete set null,
    sort_order        integer not null default 0,
    created_at        timestamptz not null default now()
);

-- Idempotent migrations for databases where `items` already existed before these columns were added.
alter table items add column if not exists person_user_id bigint references users(id) on delete cascade;
alter table items add column if not exists sort_order integer not null default 0;

-- One-time backfill: give existing rows a stable order within their own (group, person, type)
-- list, based on creation order. Only touches rows still at the untouched default (0), so
-- re-running this is safe and never clobbers a manual reorder done later via the app.
update items set sort_order = sub.rn
from (
    select id, row_number() over (
        partition by group_id, person_user_id, type
        order by created_at
    ) as rn
    from items
) sub
where items.id = sub.id and items.sort_order = 0;

create index if not exists idx_items_group_id on items(group_id);
create index if not exists idx_items_person_user_id on items(person_user_id);
create index if not exists idx_group_members_user_id on group_members(user_id);
create index if not exists idx_group_members_group_id on group_members(group_id);
