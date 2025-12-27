"""
Streamlit Chat UI for News Q&A.

Uses FastAPI backend for Q&A search and generation via Elasticsearch and LLM.
"""

import streamlit as st
from api_client import api_client, format_qa_response

# Page config
st.set_page_config(
    page_title="News Q&A Chat",
    page_icon="📰",
    layout="centered"
)

# Check backend health on load
if "backend_healthy" not in st.session_state:
    st.session_state.backend_healthy = api_client.is_healthy()

# Sidebar with backend status and stats
with st.sidebar:
    st.header("Backend Status")

    # Health indicator
    if st.session_state.backend_healthy:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Disconnected")
        st.caption("Start the FastAPI server:")
        st.code("uvicorn main:app --reload", language="bash")

    # Refresh health check
    if st.button("Refresh Status", use_container_width=True):
        st.session_state.backend_healthy = api_client.is_healthy()
        st.rerun()

    st.divider()

    # Elasticsearch stats
    if st.session_state.backend_healthy:
        st.header("Elasticsearch Index")
        stats = api_client.get_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", stats.get("document_count", 0))
        with col2:
            st.metric("Size", stats.get("index_size_human", "N/A"))

        health = stats.get("health", "unknown")
        if health == "green":
            st.success(f"Health: {health}")
        elif health == "yellow":
            st.warning(f"Health: {health}")
        else:
            st.info(f"Health: {health}")

        # # Clear index button
        # if st.button("Clear Index", use_container_width=True, type="secondary"):
        #     try:
        #         api_client.clear_index()
        #         st.success("Index cleared!")
        #         st.rerun()
        #     except Exception as e:
        #         st.error(f"Error: {e}")

    st.divider()
    st.caption("Q&A pairs are stored in Elasticsearch and searched using BM25 ranking.")

# Main chat area
st.title("📰 News Q&A Chat")
st.caption("Ask about any news topic - I'll search existing Q&As or generate new ones!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about news..."):
    # Check backend health first
    if not st.session_state.backend_healthy:
        st.session_state.backend_healthy = api_client.is_healthy()

    if not st.session_state.backend_healthy:
        st.error("Backend API is not available. Please start the FastAPI server.")
    else:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response from API
        with st.chat_message("assistant"):
            with st.spinner("Searching Q&A database..."):
                try:
                    response = api_client.search(
                        query=prompt,
                        top_k=10,
                        fallback_to_llm=True
                    )
                    formatted_response = format_qa_response(response)
                except Exception as e:
                    formatted_response = f"Error connecting to backend: {e}"

            st.markdown(formatted_response)

        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": formatted_response})
