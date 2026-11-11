# STEP 3 — "The full AI app" (app.py and checkpoints/cp3_ai.py are the same file)
# New in this version: optional resume upload, structured (JSON) answers from
# Gemini, a visual dashboard, a Markdown download and follow-up questions.

import json
import time

import streamlit as st
from google import genai
from google.genai import errors, types

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------
# Models are tried in order. If one is busy (503) or out of free quota (429),
# the app retries it once, then moves on to the next one.
MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]
TEMPORARY_ERRORS = {429, 500, 503, 504}
MAX_RESUME_MB = 15  # Gemini accepts files sent this way up to about 20 MB

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

# ---------------------------------------------------------------------------
# 2. INSTRUCTIONS FOR THE AI
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a friendly, honest career counsellor for students and job seekers in India.
You get a person's profile, and sometimes their resume as a PDF. Build a career plan for them.

What to include:
- roles: exactly 3 roles that fit this person. For each: the job title, one sentence on why it fits
  them, a match_score from 0 to 100, and a typical entry-level salary range in India in LPA
  as text, for example "3-5 LPA". This is only indicative.
- skill_gaps: 4 to 6 skills they need for these roles, most important first. For each: their
  current_level and the needed_level on a 0-10 scale, and one free resource to start learning it.
- roadmap: three blocks (days 1-30, 31-60, 61-90). Each block has exactly 3 concrete tasks that fit
  the hours per week they gave, and one small mini_project to build at the end of the block.
- todays_action: one action they can finish today in under 30 minutes.

If a resume is attached, use it to judge their skills and experience. If the resume and the
typed skills disagree, trust the resume.

Rules: be encouraging but realistic, use simple English, and never promise a job or a salary."""

FOLLOWUP_PROMPT = """You are a friendly, honest career counsellor for students and job seekers in India.
You already made the career plan below (as JSON) for this person. Answer their follow-up question
about it in simple English, in under 150 words. Be encouraging but realistic, and never promise
a job or a salary."""

# ---------------------------------------------------------------------------
# 3. THE SHAPE OF THE ANSWER (JSON SCHEMA)
# ---------------------------------------------------------------------------
# This tells Gemini exactly which fields to send back, so the app can draw
# cards, charts and checkboxes instead of showing one long block of text.
S = types.Schema
T = types.Type

ROADMAP_BLOCK = S(
    type=T.OBJECT,
    properties={
        "tasks": S(type=T.ARRAY, items=S(type=T.STRING), min_items=3, max_items=3),
        "mini_project": S(type=T.STRING),
    },
    required=["tasks", "mini_project"],
)

PLAN_SCHEMA = S(
    type=T.OBJECT,
    properties={
        "roles": S(
            type=T.ARRAY, min_items=3, max_items=3,
            items=S(
                type=T.OBJECT,
                properties={
                    "title": S(type=T.STRING),
                    "why_it_fits": S(type=T.STRING),
                    "match_score": S(type=T.INTEGER, minimum=0, maximum=100),
                    "salary_range_lpa": S(type=T.STRING),
                },
                required=["title", "why_it_fits", "match_score", "salary_range_lpa"],
            ),
        ),
        "skill_gaps": S(
            type=T.ARRAY, min_items=4, max_items=6,
            items=S(
                type=T.OBJECT,
                properties={
                    "skill": S(type=T.STRING),
                    "current_level": S(type=T.INTEGER, minimum=0, maximum=10),
                    "needed_level": S(type=T.INTEGER, minimum=0, maximum=10),
                    "free_resource": S(type=T.STRING),
                },
                required=["skill", "current_level", "needed_level", "free_resource"],
            ),
        ),
        "roadmap": S(
            type=T.OBJECT,
            properties={
                "days_1_30": ROADMAP_BLOCK,
                "days_31_60": ROADMAP_BLOCK,
                "days_61_90": ROADMAP_BLOCK,
            },
            required=["days_1_30", "days_31_60", "days_61_90"],
        ),
        "todays_action": S(type=T.STRING),
    },
    required=["roles", "skill_gaps", "roadmap", "todays_action"],
)

ROADMAP_TABS = [("days_1_30", "Days 1-30"), ("days_31_60", "Days 31-60"), ("days_61_90", "Days 61-90")]

# ---------------------------------------------------------------------------
# 4. TALKING TO GEMINI
# ---------------------------------------------------------------------------
def call_gemini(contents, config):
    """Send a request, retrying busy models and falling back to the next one."""
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
        # google-genai 3.x defaults to the v1 API, which rejects system_instruction.
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    last_error = None
    for model in MODELS:
        for attempt in range(2):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except errors.APIError as e:
                if e.code not in TEMPORARY_ERRORS:
                    raise  # e.g. a bad key: retrying will not help
                last_error = e
                if attempt == 0:
                    time.sleep(2)
    raise last_error


def make_plan(profile_text, pdf_bytes):
    """Ask Gemini for a career plan and turn its JSON answer into a Python dict."""
    contents = [profile_text]
    if pdf_bytes:
        # The resume goes straight from memory to Gemini. It is never saved to disk.
        contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.7,
        response_mime_type="application/json",
        response_schema=PLAN_SCHEMA,
    )
    response = call_gemini(contents, config)
    if not response.text:
        raise ValueError("empty answer")
    return json.loads(response.text)


def answer_followup(plan, history, question):
    """Answer a follow-up question, using the plan and earlier questions as context."""
    chat = "\n".join(f"{who}: {text}" for who, text in history)
    contents = f"Career plan:\n{json.dumps(plan)}\n\nEarlier chat:\n{chat}\n\nNew question: {question}"
    config = types.GenerateContentConfig(system_instruction=FOLLOWUP_PROMPT, temperature=0.7)
    return call_gemini(contents, config).text or "Sorry, I could not answer that. Please try again."


def friendly_error(e):
    """Turn a technical error into a message a beginner can act on."""
    if isinstance(e, KeyError):
        return "No API key found. Add it to .streamlit/secrets.toml (see the README)."
    if isinstance(e, errors.APIError):
        if e.code in TEMPORARY_ERRORS:
            return "Gemini is very busy right now. Wait a minute and try again."
        if e.code in (400, 401, 403) and "API key" in str(e):
            return "Your Gemini API key was rejected. Check .streamlit/secrets.toml."
    if isinstance(e, ValueError):  # includes json.JSONDecodeError
        return "The AI's answer was incomplete. Please try again."
    return f"Something went wrong: {e}"


# ---------------------------------------------------------------------------
# 5. TURNING THE PLAN INTO A MARKDOWN FILE (for the download button)
# ---------------------------------------------------------------------------
def plan_to_markdown(plan, name):
    lines = [f"# Career plan for {name}", "", f"**Do this today:** {plan['todays_action']}", ""]

    lines += ["## 3 roles that fit you", ""]
    for role in plan["roles"]:
        lines += [
            f"### {role['title']} ({role['match_score']}% match)",
            role["why_it_fits"],
            f"Salary: {role['salary_range_lpa']} (indicative)",
            "",
        ]

    lines += ["## Your skill gaps", "", "| Skill | Now | Needed | Free resource |", "|---|---|---|---|"]
    for gap in plan["skill_gaps"]:
        lines.append(f"| {gap['skill']} | {gap['current_level']}/10 | {gap['needed_level']}/10 | {gap['free_resource']} |")
    lines.append("")

    lines += ["## Your 90-day roadmap", ""]
    for key, label in ROADMAP_TABS:
        block = plan["roadmap"][key]
        lines.append(f"### {label}")
        lines += [f"- [ ] {task}" for task in block["tasks"]]
        lines += [f"- [ ] **Mini project:** {block['mini_project']}", ""]

    lines += ["---", "_AI suggestions, not guarantees._"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. PAGE HEADER AND INPUTS
# ---------------------------------------------------------------------------
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

# Step 1: optional resume. Streamlit keeps the uploaded file in memory only.
with st.container(border=True):
    st.markdown('<div class="step">Step 1 · Resume (optional)</div>', unsafe_allow_html=True)
    resume = st.file_uploader("Upload your resume (optional)", type="pdf", label_visibility="collapsed")
    resume_bytes = resume.getvalue() if resume else None
    if resume_bytes and len(resume_bytes) > MAX_RESUME_MB * 1024 * 1024:
        st.warning(f"That PDF is over {MAX_RESUME_MB} MB. Please upload a smaller file.")
        resume_bytes = None

# Step 2: the profile form, laid out in two columns
with st.form("profile"):
    st.markdown('<div class="step">Step 2 · About you</div>', unsafe_allow_html=True)
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


def build_profile():
    text = (
        f"Name: {name}\nEducation: {education}\nCurrent status: {status}\n"
        f"Skills: {skills or '(not typed, see resume)'}\nInterests: {interests}\nGoal: {goal}\n"
        f"Hours per week available: {hours}"
    )
    if resume_bytes:
        text += "\nA resume is attached as a PDF."
    return text


# ---------------------------------------------------------------------------
# 7. MAKING THE PLAN
# ---------------------------------------------------------------------------
# The plan is saved in st.session_state. Streamlit re-runs this whole file on
# every click (a checkbox, a question), and without saving it the plan would vanish.
if submitted:
    # Check the required boxes. The grey example text in a box does not count:
    # the box is still empty until you type something yourself.
    missing = []
    if not name.strip():
        missing.append("**Your name**")
    if not goal.strip():
        missing.append("**Your goal**")
    if not (skills.strip() or resume_bytes):
        missing.append("**Skills you already have** (or upload a resume)")
    if missing:
        st.warning("Please fill in: " + ", ".join(missing) + ". The grey example text does not count.")
    else:
        error = None
        # Only the AI call runs inside the spinner, so it always clears.
        with st.spinner("Thinking about your career..."):
            try:
                plan = make_plan(build_profile(), resume_bytes)
            except Exception as e:
                error = friendly_error(e)
        if error:
            st.error(error)
        else:
            st.session_state["plan"] = plan
            st.session_state["plan_name"] = name
            st.session_state["plan_id"] = st.session_state.get("plan_id", 0) + 1  # resets the checkboxes
            st.session_state["followups"] = []

# ---------------------------------------------------------------------------
# 8. THE DASHBOARD
# ---------------------------------------------------------------------------
if "plan" in st.session_state:
    plan = st.session_state["plan"]
    plan_id = st.session_state["plan_id"]
    st.divider()

    # Today's action, highlighted at the very top
    st.success(f"**✅ Do this today:** {plan['todays_action']}")

    # Role cards: 3 side by side
    st.subheader("🧭 3 roles that fit you")
    for column, role in zip(st.columns(3), plan["roles"]):
        with column, st.container(border=True):
            score = max(0, min(100, int(role["match_score"])))
            st.markdown(f"#### {role['title']}")
            st.markdown(f'<div class="score">{score}% <span>match</span></div>', unsafe_allow_html=True)
            st.progress(score / 100)
            st.write(role["why_it_fits"])
            st.markdown(f"💰 {role['salary_range_lpa']} *(indicative)*")

    # Skill gaps: current vs needed level as a horizontal bar chart
    st.subheader("📊 Your skill gaps")
    gaps = plan["skill_gaps"]
    chart_box = st.container(border=True)
    chart_box.bar_chart(
        {
            "Skill": [g["skill"] for g in gaps],
            "Current level": [g["current_level"] for g in gaps],
            "Needed level": [g["needed_level"] for g in gaps],
        },
        x="Skill",
        y=["Current level", "Needed level"],
        horizontal=True,
        stack=False,
        color=["#94A3B8", "#2563EB"],
        x_label="Level (0-10)",
        y_label="",
    )
    chart_box.markdown("**Free resources to start**")
    for g in gaps:
        chart_box.markdown(f"- **{g['skill']}:** {g['free_resource']}")

    # 90-day roadmap: one tab per month, tasks as checkboxes
    st.subheader("🗓️ Your 90-day roadmap")
    for tab, (key, label) in zip(st.tabs([label for _, label in ROADMAP_TABS]), ROADMAP_TABS):
        with tab:
            block = plan["roadmap"][key]
            for i, task in enumerate(block["tasks"]):
                st.checkbox(task, key=f"task_{plan_id}_{key}_{i}")
            st.info(f"🛠️ **Mini project:** {block['mini_project']}")

    # Download the plan as a Markdown file
    st.download_button(
        "⬇️ Download my plan",
        data=plan_to_markdown(plan, st.session_state["plan_name"]),
        file_name="career-plan.md",
        mime="text/markdown",
        type="primary",
        width="stretch",
    )

    # -----------------------------------------------------------------------
    # 9. FOLLOW-UP QUESTIONS
    # -----------------------------------------------------------------------
    st.subheader("💬 Ask about your plan")
    history = st.session_state["followups"]
    question = st.chat_input("Ask a follow-up question about your plan")
    if question:
        error = None
        with st.spinner("Thinking..."):
            try:
                answer = answer_followup(plan, history, question)
            except Exception as e:
                error = friendly_error(e)
        if error:
            st.error(error)
        else:
            history += [("You", question), ("Counsellor", answer)]

    for who, text in history:
        with st.chat_message("user" if who == "You" else "assistant"):
            st.markdown(text)

# ---------------------------------------------------------------------------
# 10. FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    '<div class="footer">Built at the Techolas AI Wing · AI suggestions, not guarantees.</div>',
    unsafe_allow_html=True,
)
