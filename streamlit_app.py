import json
from contextlib import closing
import threading
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import uvicorn

from backend.api import app as fastapi_app
from db.storage import get_connection, query_memories, set_permission, store_memory, delete_memory, get_permissions
from db.keyring import configured_cipher, KeyConfigurationError

st.set_page_config(page_title="Memoria | PHI369 Memory", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at top, #1a1a28, #0b0b12 45%); color: #f4f1e8; }
    .mem-card { background: rgba(255, 178, 102, 0.09); border: 1px solid rgba(255,178,102,0.26); border-radius: 14px; padding: 14px; margin-bottom: 10px; }
    .badge {display:inline-block;padding:3px 8px;border-radius:999px;background:#ffb26633;color:#ffca8a;margin-right:8px;font-size:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def start_api():
    def run():
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8765, log_level="warning")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return True


def sidebar():
    st.sidebar.title("PHI369 Memory")
    st.sidebar.caption("Trusted local operator interface")
    st.sidebar.code("/memoria/store\n/memoria/query\n/memoria/recall")
    st.sidebar.info("Application routes require credentials and explicit permissions. Semantic recall is held.")


def dashboard_page(memories):
    st.subheader("Memory Dashboard")
    total = len(memories)
    recent = memories[:5]
    by_app = pd.Series([m["app_name"] for m in memories]).value_counts().rename_axis("app_name").reset_index(name="count") if memories else pd.DataFrame(columns=["app_name", "count"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Loaded Memories", total)
    c2.metric("Apps in view", len({m['app_name'] for m in memories}))
    c3.metric("Unique Agents", len({m['agent_id'] for m in memories}))

    if memories:
        df = pd.DataFrame(memories)
        df["date"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.date
        timeline = df.groupby("date").size().reset_index(name="count")
        fig = px.line(timeline, x="date", y="count", title="Growth Timeline")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Recent Entries")
    for m in recent:
        with st.container(border=True):
            st.text(m["app_name"])
            st.text(m["content"][:180])

    st.markdown("### Most Active Apps")
    if not by_app.empty:
        st.dataframe(by_app, use_container_width=True)


def explorer_page(memories):
    st.subheader("Memory Explorer")
    apps = sorted({m["app_name"] for m in memories})
    tags = sorted({tag for m in memories for tag in m["tags"]})
    q = st.text_input("Search memories")
    col1, col2 = st.columns(2)
    app_filter = col1.selectbox("Filter by app", ["All"] + apps)
    tag_filter = col2.selectbox("Filter by tag", ["All"] + tags)

    filtered = []
    for m in memories:
        if app_filter != "All" and m["app_name"] != app_filter:
            continue
        if tag_filter != "All" and tag_filter not in m["tags"]:
            continue
        if q and q.casefold() not in (m["content"] + " " + json.dumps(m["metadata"], ensure_ascii=False)).casefold():
            continue
        filtered.append(m)

    for m in filtered:
        with st.container(border=True):
            st.text(f"#{m['id']} | {m['app_name']} | {m['agent_id']}")
            st.text(m["content"][:280])
            st.text(f"{m['timestamp']} | tags: {', '.join(m['tags'])}")


def write_page(cn):
    st.subheader("Write & Ingest")
    captured = st.session_state.pop("capture_receipt", None)
    if captured is not None:
        st.success(f"Stored memory #{captured}. Vector indexing is held.")
    with st.form("quick_capture"):
        content = st.text_area("Memory")
        app_name = st.text_input("App name", value="Memoria")
        agent_id = st.text_input("Agent ID", value="manual-user")
        tags = st.text_input("Tags (comma separated)")
        importance = st.slider("Importance", 0.0, 1.0, 0.6)
        submitted = st.form_submit_button("Quick Capture")
    if submitted and content.strip():
        payload = {
            "content": content,
            "app_name": app_name,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": [x.strip() for x in tags.split(",") if x.strip()],
            "importance_score": importance,
            "metadata": {"source": "quick_capture"},
        }
        try:
            cipher = configured_cipher()
        except KeyConfigurationError:
            st.error("Encryption configuration unavailable. No memory stored.")
            return
        mid = store_memory(cn, payload, cipher)
        st.session_state["capture_receipt"] = mid
        st.rerun()

    st.info("Application writes require a provisioned bearer credential and native write permission. See the README for the local client.")


def privacy_page(cn, memories):
    st.subheader("Privacy & Control Center")
    default_apps = ["Agentora", "Growora", "Mindora", "Reconnect", "CoEvo"]
    existing = {p["app_name"]: p for p in get_permissions(cn)}
    for app in sorted(set(default_apps) | set(existing) | {m["app_name"] for m in memories}):
        p = existing.get(app, {"can_read": 0, "can_write": 0})
        c1, c2, c3 = st.columns([2, 2, 1])
        can_read = c1.toggle(f"{app} can read", value=bool(p["can_read"]), key=f"r_{app}")
        can_write = c2.toggle(f"{app} can write", value=bool(p["can_write"]), key=f"w_{app}")
        if c3.button("Save", key=f"s_{app}"):
            set_permission(cn, app, can_read, can_write)

    receipt = st.session_state.pop("forget_receipt", None)
    if receipt is not None:
        if receipt["status"] == "LOGICALLY_DELETED":
            st.warning("Logical SQL deletion recorded. Vector cleanup is pending; external copies are unverified.")
        else:
            st.info("No memory or existing deletion intent found for that ID.")

    st.markdown("### Export")
    export_data = json.dumps(memories, indent=2)
    st.warning("Export contains only the loaded view (up to 1,000 rows), potentially decrypted. It is not an encrypted backup.")
    st.download_button("Export loaded snapshot (.memoria)", data=export_data, file_name="memoria-snapshot.memoria", mime="application/json")

    st.markdown("### Forget Memory")
    mem_id = st.number_input("Memory ID to forget", min_value=1, step=1)
    st.caption("Logical SQL deletion only. Historical vectors, exports and backups remain unverified.")
    confirmed = st.checkbox("Confirm logical deletion of this memory ID", key=f"forget_confirm_{int(mem_id)}")
    if st.button("Delete from SQL and record cleanup obligation", disabled=not confirmed):
        with closing(get_connection()) as deletion_conn:
            receipt = delete_memory(deletion_conn, int(mem_id))
        st.session_state["forget_receipt"] = receipt
        st.rerun()


def recall_page():
    st.subheader("Scoped Recall & Synthesis")
    st.info("The authenticated API supports bounded lexical recall at POST /memoria/recall. Vector recall remains held; this operator UI does not impersonate an application.")

    st.markdown("### Auto-Synthesis")
    window = st.radio("Window", ["daily", "weekly"], horizontal=True)
    if st.button("Generate synthesis"):
        st.info("Application synthesis requires a scoped credential. Use the local API client; this operator UI does not impersonate an application.")


def main():
    start_api()
    sidebar()
    st.title("Memoria | PHI369 Memory")
    st.caption("R11 research candidate · Trusted local operator · Synthetic data only")
    st.warning("Do not expose Streamlit or the API to a network. Production and sensitive-data use remain held.")
    try:
        cipher = configured_cipher()
    except KeyConfigurationError:
        st.error("Encryption configuration unavailable. Memory access is held.")
        return
    with closing(get_connection()) as cn:
        memories = query_memories(cn, limit=1000, cipher=cipher)
        st.caption("Current view: up to 1,000 recent SQL records, not a complete vault census.")
        tabs = st.tabs(["Dashboard", "Explorer", "Write", "Privacy", "Recall"])
        with tabs[0]:
            dashboard_page(memories)
        with tabs[1]:
            explorer_page(memories)
        with tabs[2]:
            write_page(cn)
        with tabs[3]:
            privacy_page(cn, memories)
        with tabs[4]:
            recall_page()


if __name__ == "__main__":
    main()
