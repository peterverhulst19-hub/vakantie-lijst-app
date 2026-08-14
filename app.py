import streamlit as st

import auth
import db

st.set_page_config(page_title="Vakantie-lijst", page_icon="\U0001f9f3")

# Streamlit stacks st.columns() vertically below its mobile breakpoint. Item rows are
# wrapped in a keyed container (below) so only those rows are forced to stay on one line;
# other multi-column layouts (e.g. the add-item form) are left free to wrap on mobile.
st.markdown(
    """
    <style>
    div[class*="st-key-item_row_"] div[data-testid="stHorizontalBlock"],
    div[class*="st-key-member_row_"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }
    div[class*="st-key-item_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child,
    div[class*="st-key-member_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        width: auto !important;
        min-width: auto !important;
        flex: 0 0 auto !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #E0F2FE 0%, #F0F9FF 280px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ITEM_TYPES = ["Kledij", "Eten", "Slapen", "Toiletgerief", "Elektronica", "Documenten", "Pharmacie", "Overig"]

pending_code = st.query_params.get("join")
user = auth.get_current_user()

if user is None:
    invited_group_name = None
    if pending_code:
        invited_group = db.get_group_by_code(pending_code)
        if invited_group:
            invited_group_name = invited_group["name"]
    auth.render_login_screen(invited_group_name)
    st.stop()

if pending_code:
    group = db.get_group_by_code(pending_code)
    if group:
        db.join_group(group["id"], user["id"])
        st.session_state["active_group_id"] = group["id"]
        st.toast(f"Toegevoegd aan '{group['name']}'")
    else:
        st.warning("Onbekende of verlopen uitnodigingscode.")
    st.query_params.clear()
    st.rerun()

# --- Sidebar: identity + group switch/create/join ---
with st.sidebar:
    st.write(f"Ingelogd als **{user['display_name'] or user['email']}**")
    st.caption(user["email"])
    if st.button("Uitloggen"):
        auth.logout()

    st.divider()

    groups = db.get_user_groups(user["id"])
    group_names = {g["id"]: g["name"] for g in groups}

    if groups:
        active_id = st.session_state.get("active_group_id")
        if active_id not in group_names:
            active_id = groups[0]["id"]
        group_ids = list(group_names.keys())
        active_id = st.selectbox(
            "Actieve groep",
            options=group_ids,
            format_func=lambda gid: group_names[gid],
            index=group_ids.index(active_id),
        )
        st.session_state["active_group_id"] = active_id
    else:
        st.session_state["active_group_id"] = None
        st.info("Je hebt nog geen groep. Maak er hieronder een aan.")

    st.divider()

    with st.expander("Nieuwe groep aanmaken"):
        with st.form("create_group_form", clear_on_submit=True):
            new_group_name = st.text_input("Naam van de groep")
            if st.form_submit_button("Aanmaken") and new_group_name.strip():
                new_group = db.create_group(new_group_name.strip(), user["id"])
                st.session_state["active_group_id"] = new_group["id"]
                st.rerun()

    with st.expander("Groep joinen via code"):
        with st.form("join_group_form", clear_on_submit=True):
            code_input = st.text_input("Uitnodigingscode")
            if st.form_submit_button("Joinen") and code_input.strip():
                found_group = db.get_group_by_code(code_input.strip())
                if found_group:
                    db.join_group(found_group["id"], user["id"])
                    st.session_state["active_group_id"] = found_group["id"]
                    st.rerun()
                else:
                    st.error("Onbekende uitnodigingscode.")

    if st.session_state.get("active_group_id"):
        with st.expander("Persoon toevoegen (bv. kind, zonder e-mail)"):
            with st.form("add_person_form", clear_on_submit=True):
                person_name = st.text_input("Naam")
                if st.form_submit_button("Toevoegen") and person_name.strip():
                    db.add_person(st.session_state["active_group_id"], person_name.strip())
                    st.rerun()

# --- Main area: active group's packing list ---
active_group_id = st.session_state.get("active_group_id")

if not active_group_id:
    st.title("\U0001f3d6️ Vakantie-lijst")
    st.write("Maak links een groep aan om te beginnen.")
    st.stop()

active_group = db.get_group(active_group_id)
st.title(f"\U0001f9f3 {active_group['name']}")

members = db.get_group_members(active_group_id)
is_owner = user["id"] == active_group["owner_user_id"]


@st.dialog("Lid verwijderen")
def _confirm_remove_member(group_id, member_id, member_label):
    st.write(f"Weet je zeker dat je **{member_label}** uit de groep wilt verwijderen?")
    st.caption(
        "Hun persoonlijke items in deze groep worden ook verwijderd, en de "
        "uitnodigingslink wordt vernieuwd. Dit kan niet ongedaan gemaakt worden."
    )
    col1, col2 = st.columns(2)
    if col1.button("Annuleren", width="stretch"):
        st.rerun()
    if col2.button("Verwijderen", type="primary", width="stretch"):
        db.remove_member(group_id, member_id)
        st.rerun()


with st.expander("Uitnodigen & leden"):
    app_base_url = st.secrets.get("app_base_url", "http://localhost:8501")
    invite_link = f"{app_base_url}/?join={active_group['invite_code']}"
    st.write("Deel deze link met anderen:")
    st.code(invite_link)
    st.write("Of enkel de code:")
    st.code(active_group["invite_code"])

    st.write("**Leden:**")
    for member in members:
        label = member["display_name"] or member["email"]
        suffix = " (eigenaar)" if member["user_id"] == active_group["owner_user_id"] else ""
        if is_owner and member["user_id"] != active_group["owner_user_id"]:
            with st.container(key=f"member_row_{member['user_id']}"):
                c1, c2 = st.columns([0.75, 0.25], vertical_alignment="center")
                c1.write(f"- {label}{suffix}")
                if c2.button("\U0001f6ab", key=f"kick_{member['user_id']}"):
                    _confirm_remove_member(active_group_id, member["user_id"], label)
        else:
            st.write(f"- {label}{suffix}")

items = db.get_items(active_group_id)
shared_items = [i for i in items if i["person_user_id"] is None]
personal_items = {}
for i in items:
    if i["person_user_id"] is not None:
        personal_items.setdefault(i["person_user_id"], []).append(i)


def _toggle(item_id: int) -> None:
    db.set_item_packed(item_id, st.session_state[f"packed_{item_id}"])


def render_packing_list(tab_items, person_user_id, key_suffix):
    total = len(tab_items)
    packed = sum(1 for i in tab_items if i["aangevinkt"])
    if total:
        st.progress(packed / total)
        st.caption(f"{packed} van {total} ingepakt")

    with st.form(f"add_item_form_{key_suffix}", clear_on_submit=True):
        item_object = st.text_input(
            "Nieuw item",
            label_visibility="collapsed",
            placeholder="bv. Zonnebrandcrème",
            key=f"obj_{key_suffix}",
        )
        col1, col2 = st.columns([1, 1.5])
        item_aantal = col1.number_input(
            "Aantal",
            min_value=1,
            value=1,
            step=1,
            label_visibility="collapsed",
            key=f"aantal_{key_suffix}",
        )
        item_type = col2.selectbox(
            "Type", ITEM_TYPES, label_visibility="collapsed", key=f"type_{key_suffix}"
        )
        add_submitted = st.form_submit_button("Toevoegen", width="stretch")
        if add_submitted and item_object.strip():
            db.add_item(
                active_group_id,
                item_object.strip(),
                int(item_aantal),
                item_type,
                user["id"],
                person_user_id,
            )
            st.rerun()

    items_by_type = {}
    for item in tab_items:
        items_by_type.setdefault(item["type"], []).append(item)

    active_types = [t for t in ITEM_TYPES if items_by_type.get(t)]
    if not active_types:
        st.caption("Nog geen items. Voeg er hierboven een toe.")
        return

    type_tabs = st.tabs(active_types)
    for type_tab, type_name in zip(type_tabs, active_types):
        with type_tab:
            for item in items_by_type[type_name]:
                with st.container(key=f"item_row_{item['id']}"):
                    c1, c2 = st.columns([0.85, 0.15])
                    label = (
                        f"{item['aantal']}x {item['object']}"
                        if item["aantal"] != 1
                        else item["object"]
                    )
                    c1.checkbox(
                        f"~~{label}~~" if item["aangevinkt"] else label,
                        value=bool(item["aangevinkt"]),
                        key=f"packed_{item['id']}",
                        on_change=_toggle,
                        args=(item["id"],),
                    )
                    if c2.button("\U0001f5d1️", key=f"del_{item['id']}"):
                        db.delete_item(item["id"])
                        st.rerun()


tab_labels = ["Gedeeld"] + [m["display_name"] or m["email"] for m in members]
tabs = st.tabs(tab_labels)

with tabs[0]:
    render_packing_list(shared_items, None, "shared")

for tab, member in zip(tabs[1:], members):
    with tab:
        render_packing_list(
            personal_items.get(member["user_id"], []), member["user_id"], f"user_{member['user_id']}"
        )
