import os
import streamlit as st
from dotenv import load_dotenv
from src.main import run_queries_synthesize

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")

# Page setup
st.set_page_config(page_title="MTG Judge Bot", layout="wide")
st.title("🧙 MTG Judge Bot")
st.markdown("Ask complex Magic: The Gathering rules questions and get smart, grounded answers from trusted sources.")

# Input field
query_text = st.text_area("Enter your Magic: The Gathering rules question:", height=200)

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = None
if "show_sources" not in st.session_state:
    st.session_state.show_sources = False

# Button: Run query
if st.button("Get Answer", type="primary") and query_text:
    with st.spinner("Consulting ancient scrolls..."):
        try:
            st.session_state.results = run_queries_synthesize(query_text=query_text)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.session_state.results = None

# Show results if available
if st.session_state.results:
    results = st.session_state.results

    # Always show final answer
    st.success("🧠 Final Answer:")
    st.markdown(results["final_answer"])

    # Toggle to show individual responses
    st.session_state.show_sources = st.toggle("🔍 Show individual source responses", value=st.session_state.show_sources)

    if st.session_state.show_sources:
        st.divider()
        st.subheader("📚 Source Breakdown")

        with st.expander("📘 RAG Database Result"):
            st.markdown(results["rag"])

        with st.expander("🌐 Google Search Result"):
            st.markdown(results["google"])

        with st.expander("👾 Reddit Search Result (API + Google Combined)"):
            st.markdown(results["reddit"])

# How to run (comment)
# Run with: streamlit run /Users/noah/Github_repos/mtg_judgebot/streamlit_app.py
# If I have a creature with an equipment on it, and an opponent gains control of the creature, what happens?