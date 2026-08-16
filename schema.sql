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

create table if not exists categories (
    id          bigserial primary key,
    group_id    bigint not null references groups(id) on delete cascade,
    name        text not null,
    created_at  timestamptz not null default now(),
    unique (group_id, name)
);

create index if not exists idx_categories_group_id on categories(group_id);

-- One-time backfill: seed the original 8 default categories for every group that doesn't
-- have ANY categories row yet. New groups created after this migration are seeded directly
-- in db.create_group(); this block only catches groups created before `categories` existed.
-- Safe to re-run: once a group has at least one categories row, the `not exists` guard makes
-- this a no-op for that group.
insert into categories (group_id, name)
select g.id, d.name
from groups g
cross join (values
    (1, 'Kledij'), (2, 'Eten'), (3, 'Slapen'), (4, 'Toiletgerief'),
    (5, 'Elektronica'), (6, 'Documenten'), (7, 'Pharmacie'), (8, 'Overig')
) as d(ord, name)
where not exists (select 1 from categories c where c.group_id = g.id)
order by g.id, d.ord;
