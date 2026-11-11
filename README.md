# 🎯 AI Career Planner

A Streamlit web app that turns your profile (and, if you like, your resume) into a personal
career plan using Google Gemini:

- **3 roles that fit you**, each with a match score and an indicative salary range in India
- **Your skill gaps**, as a chart of current vs needed level, with a free resource for each skill
- **A 90-day roadmap** split into 3 months, with tasks you can tick off and a mini project for each month
- **One thing to do today**
- A **Markdown download** of the plan, and **follow-up questions** about it

Built with [Streamlit](https://streamlit.io) and the [google-genai](https://pypi.org/project/google-genai/)
library. These two are the only dependencies.

---

## Run it locally

You need **Python 3.10+** and a free **Gemini API key**.

**1. Install**

```bash
cd ai-career-planner
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add your API key**

1. Get a free key at <https://aistudio.google.com/apikey> (sign in → **Create API key** → copy).
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
3. Paste your key between the quotes:

   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```

   Keep the straight double quotes around the key.

**3. Start the app**

```bash
streamlit run app.py
```

Open <http://localhost:8501>. Press `Ctrl+C` in the terminal to stop it.

> **Keep your key private.** `.streamlit/secrets.toml` is listed in `.gitignore`, so Git never
> pushes it. When you deploy (for example to Streamlit Community Cloud), paste the key into the
> host's **Secrets** settings instead of committing it.

### Running in GitHub Codespaces

The repo includes a `.devcontainer/` setup. Open the repo in a Codespace and the dependencies
install and the app starts on port 8501 by themselves. You still need to add
`.streamlit/secrets.toml` as in step 2.

---

## Project structure

```
ai-career-planner/
├── app.py                      # The app you run (same as checkpoints/cp3_ai.py)
├── requirements.txt            # streamlit, google-genai
├── checkpoints/                # The learning path: one file per step
│   ├── cp1_hello.py            #   Step 1: hello page
│   ├── cp2_form.py             #   Step 2: the profile form
│   └── cp3_ai.py               #   Step 3: the full AI app
├── .streamlit/
│   ├── config.toml             # Theme (light, primary colour #2563EB)
│   ├── secrets.toml.example    # Template for your API key
│   └── secrets.toml            # Your real key (you create this; never committed)
└── .devcontainer/              # Setup for GitHub Codespaces
```

### How `app.py` is organised

The file is split into numbered sections, each with a plain-English comment:

| # | Section | What it does |
|---|---|---|
| 1 | Setup | Imports, the list of models to try, page layout and a little CSS |
| 2 | Instructions for the AI | The system prompt: tone, rules and what to include |
| 3 | Shape of the answer | A JSON schema, so Gemini returns fields the app can draw |
| 4 | Talking to Gemini | `call_gemini` (retries and model fallback), `make_plan`, `answer_followup`, `friendly_error` |
| 5 | Markdown export | `plan_to_markdown` turns the plan into a file to download |
| 6 | Header and inputs | Optional resume upload + the profile form |
| 7 | Making the plan | Checks the form, calls Gemini, saves the plan in `st.session_state` |
| 8 | Dashboard | Today box, role cards, skill-gap chart, roadmap tabs, download button |
| 9 | Follow-up questions | A chat box that answers questions about your plan |
| 10 | Footer | |

### How a request flows

```
form + optional resume PDF ──► make_plan() ──► call_gemini() ──► Gemini (JSON matching PLAN_SCHEMA)
                                                                        │
            dashboard ◄── st.session_state["plan"] ◄── json.loads() ◄───┘
```

- **Resume:** the PDF is held in memory only and sent to Gemini together with the form. It is
  never saved to disk. If the resume and the typed skills disagree, the AI is told to trust the resume.
- **Reliability:** if a model is busy (503) or over its free quota (429), `call_gemini` waits and
  retries once, then moves on to the next model in `MODELS`
  (`gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-flash-lite-latest`).
- **Session state:** Streamlit reruns the whole script on every click. The plan is saved in
  `st.session_state`, so ticking a checkbox or asking a question doesn't wipe it.

---

## Learning path: build it step by step

Each file in `checkpoints/` is a complete, runnable app that adds one idea to the step before it.
To try a step on its own:

```bash
streamlit run checkpoints/cp1_hello.py
```

You can also copy a step's contents into `app.py`. All steps share the same layout and theme, so
the look stays the same as you go.

### Step 1: Hello, Streamlit (`cp1_hello.py`)
**You learn:** how a Streamlit script turns into a web page, and how it reruns from top to bottom
whenever you change an input.
**Try it:** type your name and see the welcome message.

### Step 2: The interface (`cp2_form.py`)
**You learn:** collecting input with `st.form` (text boxes, a dropdown, radio buttons, a slider)
and checking that the required fields are filled. There is no AI yet: the button shows the
exact data the AI *will* receive.
**Try it:** submit with a box empty, then with everything filled in.

### Step 3: The full AI app (`cp3_ai.py` = `app.py`)
This step connects the form to Gemini and builds the full product. Read the sections of the
file in this order:

1. **Connect to Gemini:** create a `genai.Client` with your key from `st.secrets` and send the
   profile with a system prompt (sections 2 and 4).
2. **Handle errors well:** retry busy models, fall back to another model, and show friendly
   messages instead of stack traces (`call_gemini`, `friendly_error`).
3. **Get structured output:** ask for JSON with `response_mime_type` and a `response_schema`,
   so the answer arrives as data, not a wall of text (section 3).
4. **Add a resume:** send an uploaded PDF to Gemini as an extra input with
   `types.Part.from_bytes` (sections 4 and 6).
5. **Build the dashboard:** columns, progress bars, a bar chart, tabs and checkboxes, all drawn
   from the JSON (section 8).
6. **Remember things between clicks:** use `st.session_state` to keep the plan, the
   checkbox ticks and the chat history (sections 7 and 9).
7. **Export and chat:** a Markdown download button and follow-up questions (sections 5 and 9).

### Ideas to take it further
- Save plans to a database so users can come back to them
- Let users pick a city to get more local salary ranges
- Add a "regenerate this role" button for each role card
- Deploy it to Streamlit Community Cloud and share the link

---

## Troubleshooting

| What you see | What to do |
|---|---|
| "No API key found" | Create `.streamlit/secrets.toml` as in step 2 of *Run it locally* |
| "Your Gemini API key was rejected" | Copy the key again from AI Studio. Keep the straight `"` quotes around it |
| "Gemini is very busy right now" | Google's servers are overloaded for a moment. Wait a minute and try again |
| "Please fill in: …" | Type in the boxes it names. The grey example text in a box doesn't count as an answer |
| A TOML error mentioning `secrets.toml` | The key line is malformed, usually because the quotes are missing |

---

*AI suggestions, not guarantees. Salary ranges are indicative only.*
