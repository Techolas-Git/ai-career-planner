# STEP 1 — "Hello, AI builder"
# The smallest Streamlit app. If this page opens in your browser,
# your setup works.
# It uses the same page layout as the final app, so the look never changes.

import streamlit as st

st.set_page_config(page_title="AI Career Planner", page_icon="🎯", layout="centered")

# A little CSS (page styling). "centered" layout keeps everything in a middle
# column; we make that column a bit wider so the 3 role cards fit side by side.
st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] { max-width: 1000px; padding-top: 2.5rem; }
    .hero { text-align: center; margin-bottom: 1.5rem; }
    .hero h1 { font-size: 2.6rem; margin-bottom: 0.2rem; }
    .hero p { color: #475569; font-size: 1.1rem; margin: 0; }
    .step { color: #2563EB; font-weight: 600; font-size: 0.85rem;
            letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.3rem; }
    .score { font-size: 2.4rem; font-weight: 700; color: #2563EB; line-height: 1.1; }
    .score span { font-size: 1rem; font-weight: 500; color: #475569; }
    .footer { text-align: center; color: #64748B; font-size: 0.85rem; padding: 0.5rem 0 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered title and subtitle
st.markdown(
    """
    <div class="hero">
      <h1>🎯 AI Career Planner</h1>
      <p>Hello! This app is running on <b>my</b> computer in the cloud.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    name = st.text_input("What's your name?")
    if name:
        st.success(f"Welcome, {name}. Let's build your first AI product.")

# Footer
st.divider()
st.markdown(
    '<div class="footer">Built at the Techolas AI Wing · AI suggestions, not guarantees.</div>',
    unsafe_allow_html=True,
)
