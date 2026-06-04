"""
RAG Chat UI — Streamlit frontend for the FastAPI + CrewAI pipeline.
Accessible at http://localhost:3000 when running via docker-compose.
"""

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")
API_KEY = os.getenv("API_KEY", "my-secret-key-123")
COLLECTION = os.getenv("COLLECTION_NAME", "default")

st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🤖",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🤖 RAG Assistant")
    st.markdown("**Powered by:** Ollama · CrewAI · Qdrant")
    st.divider()

    st.subheader("📄 Ingest Document")
    uploaded = st.file_uploader(
        "Upload PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        help="Max 50 MB",
    )
    collection_name = st.text_input("Collection", value=COLLECTION)

    if st.button("Ingest", disabled=uploaded is None, use_container_width=True):
        with st.spinner("Ingesting…"):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/v1/ingest-documents",
                    headers={"X-API-Key": API_KEY},
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/octet-stream")},
                    data={"collection_name": collection_name},
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(
                        f"✅ **{data['filename']}** ingested\n\n"
                        f"{data['chunks_stored']} chunks stored in `{data['collection']}`"
                    )
                else:
                    st.error(f"Error {resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    st.divider()

    st.subheader("⚙️ Settings")
    top_k = st.slider("Top-K chunks", min_value=1, max_value=20, value=5)
    show_sources = st.toggle("Show source chunks", value=True)
    show_metrics = st.toggle("Show latency + model", value=True)

    st.divider()
    st.caption("🏥 [Health check](%s/api/v1/health)" % API_URL)
    st.caption("📖 [API docs](%s/docs)" % API_URL)


# ── Chat area ─────────────────────────────────────────────────────────────────

st.title("💬 Chat with your documents")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I'm your RAG assistant. Upload a document in the sidebar, "
                "then ask me anything about it.\n\n"
                "You can also ask me to **run tests** or **check system health**."
            ),
        }
    ]

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📚 {len(msg['sources'])} source chunk(s)"):
                for i, src in enumerate(msg["sources"], 1):
                    page_info = f", page {src['page']}" if src.get("page") else ""
                    st.markdown(
                        f"**[{i}] {src['filename']}{page_info}** — score: `{src['score']:.3f}`\n\n"
                        f"> {src['excerpt'][:300]}"
                    )
        if msg.get("metrics"):
            m = msg["metrics"]
            st.caption(f"⏱ {m['latency_ms']} ms · 🤖 {m['model_used']}")

# Input
if prompt := st.chat_input("Ask a question about your documents…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/v1/query",
                    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                    json={
                        "question": prompt,
                        "collection_name": collection_name,
                        "top_k": top_k,
                    },
                    timeout=180,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    metrics = {
                        "latency_ms": data.get("latency_ms", 0),
                        "model_used": data.get("model_used", ""),
                    }

                    st.markdown(answer)

                    if show_sources and sources:
                        with st.expander(f"📚 {len(sources)} source chunk(s)"):
                            for i, src in enumerate(sources, 1):
                                page_info = f", page {src['page']}" if src.get("page") else ""
                                st.markdown(
                                    f"**[{i}] {src['filename']}{page_info}** "
                                    f"— score: `{src['score']:.3f}`\n\n"
                                    f"> {src['excerpt'][:300]}"
                                )

                    if show_metrics:
                        st.caption(
                            f"⏱ {metrics['latency_ms']} ms · 🤖 {metrics['model_used']}"
                        )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources if show_sources else [],
                        "metrics": metrics if show_metrics else {},
                    })

                elif resp.status_code == 404:
                    msg = "⚠️ No collection found. Please ingest a document first using the sidebar."
                    st.warning(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})

                else:
                    msg = f"❌ API error {resp.status_code}: {resp.text[:300]}"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})

            except httpx.ConnectError:
                msg = "❌ Cannot reach the API. Make sure docker compose is running."
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
            except Exception as e:
                msg = f"❌ Unexpected error: {e}"
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
