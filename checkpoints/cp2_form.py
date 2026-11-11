# STEP 2 — "The interface"
# The form collects everything the AI will need. No AI yet:
# pressing the button just shows what the AI *will* receive.
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
      <p>Tell me about yourself. I'll suggest roles, skill gaps and a 90-day plan.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# The profile form, laid out in two columns
with st.form("profile"):
    st.markdown('<div class="step">About you</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    name = left.text_input("Your name")
    education = right.selectbox(
        "Highest education",
        ["Plus Two / 12th", "Diploma", "B.Tech / B.E.", "B.Sc / BCA",
         "B.Com / BBA", "BA", "Master's degree", "Other"],
    )
    status = st.radio(
        "Where are you right now?",
        ["Student", "Graduate looking for a job", "Working, want to switch", "Career break"],
        horizontal=True,
    )
    left, right = st.columns(2)
    skills = left.text_area("Skills you already have", placeholder="Excel, basic Python, communication...")
    interests = right.text_area("What do you enjoy?", placeholder="Solving puzzles, design, talking to people...")
    goal = st.text_input("Your goal", placeholder="Get my first job in tech within 6 months")
    hours = st.slider("Hours per week you can study", 2, 40, 10)
    submitted = st.form_submit_button("🚀 Plan my career", type="primary", width="stretch")

if submitted:
    # Check the required boxes. The grey example text in a box does not count:
    # the box is still empty until you type something yourself.
    missing = []
    if not name.strip():
        missing.append("**Your name**")
    if not goal.strip():
        missing.append("**Your goal**")
    if not skills.strip():
        missing.append("**Skills you already have**")
    if missing:
        st.warning("Please fill in: " + ", ".join(missing) + ". The grey example text does not count.")
    else:
        st.subheader("What the AI will receive")
        st.json({
            "name": name, "education": education, "status": status,
            "skills": skills, "interests": interests, "goal": goal,
            "hours_per_week": hours,
        })

# Footer
st.divider()
st.markdown(
    '<div class="footer">Built at the Techolas AI Wing · AI suggestions, not guarantees.</div>',
    unsafe_allow_html=True,
)
