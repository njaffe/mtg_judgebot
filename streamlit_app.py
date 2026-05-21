import os
import streamlit as st
from dotenv import load_dotenv
from src.cli.main import MTGJudgeCLI

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")

# Page setup
st.set_page_config(page_title="MTG Judge Bot", layout="wide")
st.title("MTG Judge Bot")
st.markdown("Ask complex Magic: The Gathering rules questions and get accurate, authoritative rulings.")

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = None
if "show_sources" not in st.session_state:
    st.session_state.show_sources = False
if "cli" not in st.session_state:
    st.session_state.cli = None

# Initialize CLI instance
if st.session_state.cli is None:
    with st.spinner("Initializing MTG Judge Bot..."):
        try:
            st.session_state.cli = MTGJudgeCLI()
        except Exception as e:
            st.error(f"Failed to initialize MTG Judge Bot: {e}")
            st.stop()

# Sidebar for advanced options
with st.sidebar:
    st.header("Options")

    enable_external = st.toggle(
        "Enable external sources (Google/Reddit)",
        value=False,
        help="When enabled, supplements the rules database with web search and Reddit community discussions.",
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

    if st.button("Refresh RAG Database", help="Rebuild the RAG database from source documents"):
        with st.spinner("Refreshing database..."):
            try:
                st.session_state.cli.refresh_rag_database()
                st.success("Database refreshed successfully!")
            except Exception as e:
                st.error(f"Failed to refresh database: {e}")

# Main input
query_text = st.text_area(
    "Enter your Magic: The Gathering rules question:",
    height=200,
    placeholder="Example: If I have a creature with an equipment on it, and an opponent gains control of the creature, what happens?",
)

# Button: Run query
if st.button("Get Answer", type="primary") and query_text:
    with st.spinner("Analyzing rules and looking up cards..."):
        try:
            st.session_state.results = st.session_state.cli.run_single_query(
                query_text=query_text,
                enable_external=enable_external,
                subreddit=subreddit,
                time_filter=time_filter,
                sort=sort_method,
                limit=limit,
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.session_state.results = None

# Show results if available
if st.session_state.results:
    results = st.session_state.results

    # Always show final answer
    st.success("Final Answer:")
    st.markdown(results["final_answer"])

    # Toggle to show individual responses
    st.session_state.show_sources = st.toggle(
        "Show source breakdown", value=st.session_state.show_sources
    )

    if st.session_state.show_sources:
        st.divider()
        st.subheader("Source Breakdown")

        if results.get("card_data"):
            with st.expander("Card Data (Scryfall)", expanded=True):
                st.text(results["card_data"])

        with st.expander("RAG Database Result (Comprehensive Rules)"):
            st.markdown(results.get("rag", "No RAG response."))

        if results.get("google"):
            with st.expander("Google Search Result"):
                st.markdown(results["google"])

        if results.get("reddit"):
            with st.expander("Reddit Search Result"):
                st.markdown(results["reddit"])

    # Usage stats
    usage = results.get("llm_usage", {})
    if usage:
        st.caption(
            f"Tokens: {usage.get('total_tokens', 0)} "
            f"(in: {usage.get('prompt_tokens', 0)}, out: {usage.get('completion_tokens', 0)}) | "
            f"Latency: {usage.get('latency_ms', 0)}ms | "
            f"Cost: ${usage.get('cost_usd', 0):.4f}"
        )

# Footer
st.divider()
st.markdown("""
**How to run:** `streamlit run streamlit_app.py`

**Example queries:**
- If I have a creature with an equipment on it, and an opponent gains control of the creature, what happens?
- Can I use a planeswalker's loyalty ability the turn it enters the battlefield?
- What happens if I cast a spell with X in its cost but don't pay for X?
""")
