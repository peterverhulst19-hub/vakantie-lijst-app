"""Database access layer: Supabase Postgres via st.connection."""
import secrets

import pandas as pd
import streamlit as st
from sqlalchemy import text


def get_conn():
    return st.connection("postgresql", type="sql")


def _clean(row: dict) -> dict:
    # pandas represents SQL NULL as NaN for some column types, and NaN is truthy in
    # Python (`nan or "fallback"` -> nan), so normalize back to None here, once, centrally.
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


def upsert_user(email: str, display_name: str | None) -> dict:
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                """
                insert into users (email, display_name)
                values (:email, :display_name)
                on conflict (email) do update
                    set display_name = coalesce(excluded.display_name, users.display_name)
                """
            ),
            {"email": email, "display_name": display_name},
        )
        s.commit()
    df = conn.query("select * from users where email = :email", params={"email": email}, ttl=0)
    return _clean(df.iloc[0].to_dict())


def create_group(name: str, owner_user_id: int) -> dict:
    conn = get_conn()
    invite_code = secrets.token_urlsafe(9)
    with conn.session as s:
        group_id = s.execute(
            text(
                """
                insert into groups (name, owner_user_id, invite_code)
                values (:name, :owner_user_id, :invite_code)
                returning id
                """
            ),
            {"name": name, "owner_user_id": owner_user_id, "invite_code": invite_code},
        ).scalar_one()
        s.execute(
            text(
                """
                insert into group_members (group_id, user_id)
                values (:group_id, :user_id)
                on conflict (group_id, user_id) do nothing
                """
            ),
            {"group_id": group_id, "user_id": owner_user_id},
        )
        s.commit()
    return get_group(group_id)


def get_group(group_id: int) -> dict | None:
    conn = get_conn()
    df = conn.query("select * from groups where id = :id", params={"id": group_id}, ttl=0)
    return None if df.empty else _clean(df.iloc[0].to_dict())


def get_group_by_code(invite_code: str) -> dict | None:
    conn = get_conn()
    df = conn.query(
        "select * from groups where invite_code = :code", params={"code": invite_code}, ttl=0
    )
    return None if df.empty else _clean(df.iloc[0].to_dict())


def get_user_groups(user_id: int) -> list[dict]:
    conn = get_conn()
    df = conn.query(
        """
        select g.*
        from groups g
        join group_members gm on gm.group_id = g.id
        where gm.user_id = :user_id
        order by g.created_at
        """,
        params={"user_id": user_id},
        ttl=0,
    )
    return [_clean(r) for r in df.to_dict("records")]


def add_person(group_id: int, display_name: str) -> dict:
    # For dependents (e.g. children) who don't have their own e-mail/Google account.
    # They get a synthetic, never-real e-mail so they still fit the `users` table's
    # unique-email identity model; nobody can ever log in as them.
    placeholder_email = f"lid-{secrets.token_hex(6)}@geen-email.lokaal"
    person = upsert_user(placeholder_email, display_name)
    join_group(group_id, person["id"])
    return person


def remove_member(group_id: int, user_id: int) -> None:
    conn = get_conn()
    new_invite_code = secrets.token_urlsafe(9)
    with conn.session as s:
        s.execute(
            text("delete from items where group_id = :group_id and person_user_id = :user_id"),
            {"group_id": group_id, "user_id": user_id},
        )
        s.execute(
            text("delete from group_members where group_id = :group_id and user_id = :user_id"),
            {"group_id": group_id, "user_id": user_id},
        )
        s.execute(
            text("update groups set invite_code = :code where id = :group_id"),
            {"code": new_invite_code, "group_id": group_id},
        )
        s.commit()


def join_group(group_id: int, user_id: int) -> None:
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                """
                insert into group_members (group_id, user_id)
                values (:group_id, :user_id)
                on conflict (group_id, user_id) do nothing
                """
            ),
            {"group_id": group_id, "user_id": user_id},
        )
        s.commit()


def get_group_members(group_id: int) -> list[dict]:
    conn = get_conn()
    df = conn.query(
        """
        select u.id as user_id, u.email, u.display_name, gm.joined_at
        from group_members gm
        join users u on u.id = gm.user_id
        where gm.group_id = :group_id
        order by gm.joined_at
        """,
        params={"group_id": group_id},
        ttl=0,
    )
    return [_clean(r) for r in df.to_dict("records")]


def get_items(group_id: int) -> list[dict]:
    conn = get_conn()
    df = conn.query(
        "select * from items where group_id = :group_id order by created_at",
        params={"group_id": group_id},
        ttl=0,
    )
    return [_clean(r) for r in df.to_dict("records")]


def add_item(
    group_id: int,
    object_name: str,
    aantal: int,
    item_type: str,
    added_by_user_id: int,
    person_user_id: int | None = None,
) -> None:
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                """
                insert into items (group_id, object, aantal, type, added_by_user_id, person_user_id)
                values (:group_id, :object, :aantal, :type, :added_by_user_id, :person_user_id)
                """
            ),
            {
                "group_id": group_id,
                "object": object_name,
                "aantal": aantal,
                "type": item_type,
                "added_by_user_id": added_by_user_id,
                "person_user_id": person_user_id,
            },
        )
        s.commit()


def set_item_packed(item_id: int, packed: bool) -> None:
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text("update items set aangevinkt = :aangevinkt where id = :id"),
            {"aangevinkt": 1 if packed else 0, "id": item_id},
        )
        s.commit()


def delete_item(item_id: int) -> None:
    conn = get_conn()
    with conn.session as s:
        s.execute(text("delete from items where id = :id"), {"id": item_id})
        s.commit()
