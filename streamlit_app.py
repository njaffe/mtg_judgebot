import os
import streamlit as st
from dotenv import load_dotenv
from src.cli.main import MTGJudgeCLI

if os.path.exists(".env"):
    load_dotenv(".env")

st.set_page_config(page_title="MTG Judge Bot", layout="wide")
st.title("MTG Judge Bot")
st.markdown("Ask complex Magic: The Gathering rules questions and get accurate, authoritative rulings.")

# Initialize session state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_sources" not in st.session_state:
    st.session_state.chat_sources = []  # parallel list; None for user turns
if "cli" not in st.session_state:
    st.session_state.cli = None

if st.session_state.cli is None:
    with st.spinner("Initializing MTG Judge Bot..."):
        try:
            st.session_state.cli = MTGJudgeCLI()
        except Exception as e:
            st.error(f"Failed to initialize MTG Judge Bot: {e}")
            st.stop()

# Sidebar options
with st.sidebar:
    st.header("Options")

    enable_external = st.toggle(
        "Enable external sources (Google/Reddit)",
        value=False,
        help="Supplements the rules database with web search and Reddit community discussions.",
    )

    if enable_external:
        st.subheader("External Source Settings")
        subreddit = st.selectbox(
            "Reddit Subreddit",
            ["mtgrules", "magictcg", "spikes", "edh", "modernmagic"],
            index=0,
        )
        time_filter = st.selectbox(
            "Reddit Time Filter",
            ["hour", "day", "week", "month", "year", "all"],
            index=4,
        )
        sort_method = st.selectbox(
            "Reddit Sort Method",
            ["relevance", "hot", "top", "new", "comments"],
            index=2,
        )
        limit = st.slider("Number of Reddit Results", 5, 25, 15)
    else:
        subreddit = "mtgrules"
        time_filter = "year"
        sort_method = "top"
        limit = 15

    st.divider()

    if st.button("Clear conversation"):
        st.session_state.chat_messages = []
        st.session_state.chat_sources = []
        st.rerun()

    if st.button("Refresh RAG Database", help="Rebuild the RAG database from source documents"):
        with st.spinner("Refreshing database..."):
            try:
                st.session_state.cli.refresh_rag_database()
                st.success("Database refreshed successfully!")
            except Exception as e:
                st.error(f"Failed to refresh database: {e}")


def _show_sources(results: dict):
    with st.expander("Sources & details"):
        if results.get("card_data"):
            st.subheader("Card Data (Scryfall)")
            st.text(results["card_data"])

        st.subheader("RAG Database (Comprehensive Rules)")
        st.markdown(results.get("rag") or "No RAG response.")

        if results.get("google"):
            st.subheader("Google Search")
            st.markdown(results["google"])

        if results.get("reddit"):
            st.subheader("Reddit")
            st.markdown(results["reddit"])

        usage = results.get("llm_usage", {})
        if usage:
            st.caption(
                f"Tokens: {usage.get('total_tokens', 0)} "
                f"(in: {usage.get('prompt_tokens', 0)}, out: {usage.get('completion_tokens', 0)}) | "
                f"Latency: {usage.get('latency_ms', 0)}ms | "
                f"Cost: ${usage.get('cost_usd', 0):.4f}"
            )


# Render existing conversation
for i, msg in enumerate(st.session_state.chat_messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        sources = st.session_state.chat_sources[i] if i < len(st.session_state.chat_sources) else None
        if sources:
            _show_sources(sources)

# Chat input
if prompt := st.chat_input("Ask an MTG rules question..."):
    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation history from prior turns (clean Q&A, not RAG prompts)
    history = list(st.session_state.chat_messages)

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    st.session_state.chat_sources.append(None)

    # Run pipeline and stream assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing rules and looking up cards..."):
            try:
                results = st.session_state.cli.run_single_query(
                    query_text=prompt,
                    enable_external=enable_external,
                    subreddit=subreddit,
                    time_filter=time_filter,
                    sort=sort_method,
                    limit=limit,
                    conversation_history=history if history else None,
                )
                answer = results["final_answer"]
            except Exception as e:
                answer = f"An error occurred: {e}"
                results = None

        st.markdown(answer)
        if results:
            _show_sources(results)

    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    st.session_state.chat_sources.append(results)
