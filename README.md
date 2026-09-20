# Row Operation — Setup Tutorial

This project has two independent pieces:

```
Comp3/
├── TUTORIAL.md              ← this file
├── backend/
│   ├── matrix_backend.py    ← core matrix engine (no web code)
│   ├── api.py               ← FastAPI wrapper, exposes it over HTTP
│   ├── requirements.txt
│   └── venv/                ← created in Section 2, Step 2 (not included)
└── frontend/
    └── index.html           ← self-contained UI (HTML + CSS + JS, no build step)
```

> A `__pycache__/` folder will also appear inside `backend/` the first time
> you run the server. That's normal — Python generates it automatically and
> you can ignore it.

The frontend is a single static HTML file — no npm, no bundler. It talks to the
backend over HTTP, so you just need the backend running first.

---

## 1. Prerequisites

- **Anaconda** (recommended) — download the Anaconda Distribution (or the
  lighter Miniconda) from anaconda.com. It bundles Python and gives you the
  **Anaconda Prompt**, which is the terminal you'll use for everything below.
- A modern browser (Chrome, Firefox, Edge, Safari)

Open **Anaconda Prompt** from the Start menu (macOS/Linux: any terminal where
Anaconda's Python is on your PATH) and check your Python version:

```
python --version
```

It should print Python 3.9 or newer.

> **Not using Anaconda?** A plain python.org install works too — see
> [Section 6](#6-anaconda--windows-notes).

---

## 2. Set up the backend

**Step 1 — Open Anaconda Prompt in the `backend/` folder:**

```
cd backend
```

(Run this from inside the `Comp3` folder. Or jump straight there from
anywhere — if you left the folder in Downloads:)

```
# Windows (Anaconda Prompt)
cd %USERPROFILE%\Downloads\Comp3\backend

# macOS/Linux
cd ~/Downloads/Comp3/backend
```

**Step 2 — Create a virtual environment (recommended):**

```
python -m venv venv
```

Activate it:

```
# macOS/Linux
source venv/bin/activate

# Windows (Anaconda Prompt, Command Prompt or PowerShell)
venv\Scripts\activate
```

Your prompt should now show `(venv)` at the start of the line. (In Anaconda
Prompt you'll see `(venv) (base)` — that's fine, it just means both are active.)

**Step 3 — Install dependencies:**

```
pip install -r requirements.txt
```

Let this fully finish — it should pull in `fastapi`, `uvicorn`, `pydantic`,
and their sub-dependencies. If `uvicorn` isn't found in the next step, this
is almost always why: come back and re-run this install (make sure `(venv)`
is showing in your prompt first).

**Step 4 — Start the server:**

```
uvicorn api:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Step 5 — Verify it's alive.** Open a second terminal (or your browser) and hit:

```
curl http://127.0.0.1:8000/health
# -> {"status":"ok"}
```

Note: visiting `http://127.0.0.1:8000` (the bare root URL) on its own will
correctly show `{"detail":"Not Found"}` — that's expected, there's no route
at `/`. Use `/health` or `/docs` (FastAPI's interactive API explorer) instead.

Leave this server running — the frontend depends on it.

> `--reload` auto-restarts the server whenever you edit `matrix_backend.py` or
> `api.py`. Great for development; drop it in production.

---

## 3. Set up the frontend

No build step needed — it's a single HTML file that runs directly in the browser.

**Option A — Just open it:**

Double-click `frontend/index.html`, or open it via `File → Open` in your browser.

**Option B — Serve it (recommended, avoids some browsers' file:// quirks):**

Open a **second Anaconda Prompt** (the first one is busy running the backend),
then:

```
cd Comp3/frontend
python -m http.server 5500
```

Then visit `http://localhost:5500` in your browser.

Either way, once the page loads you should see **`[ BACKEND ONLINE ]`** in
the top-right status indicator. If it says **`[ BACKEND UNREACHABLE ]`**,
double-check the backend server from Section 2 is still running on port 8000.

---

## 4. Using the app

1. **Set the matrix size** with the row/column steppers under `[ MATRIX ]`,
   then fill in the grid. Fractions like `3/2` are accepted directly.
2. **Add up to 3 row operations** under `[ OPERATIONS ]` — Scaling,
   Interchange, or Replacement — filling in the row(s) and factor each needs.
3. Click **RUN OPERATIONS**.
4. The `[ TRACE ]` panel on the right fills in as one continuous log, top to bottom:
   - the **original matrix** you entered
   - **each step**, showing the exact operation applied (e.g.
     `R2 -> R2 + 3/2 * R1`) directly above the matrix it produced, with the
     row(s) that changed outlined in red
   - the **final matrix**, set apart in its own highlighted block at the bottom

Nothing is hidden behind tabs — scroll down to see the whole derivation at once.

---

## 5. Connecting frontend to a different backend URL

The frontend is hardcoded to call `http://127.0.0.1:8000`. If you deploy the
backend elsewhere (a server, a container, a different port), update this one
line near the top of the `<script>` block in `index.html`:

```js
const API_BASE = "http://127.0.0.1:8000";
```

Change it to wherever your backend actually lives, e.g.:

```js
const API_BASE = "https://your-api.example.com";
```

---

## 6. Anaconda & Windows notes

### Coming back later

Every time you open a new Anaconda Prompt, reactivate the venv before
starting the server:

```
cd backend
venv\Scripts\activate          # source venv/bin/activate on macOS/Linux
uvicorn api:app --reload --port 8000
```

You only need to run `python -m venv venv` and `pip install` once.

### Always use Anaconda Prompt

- Use **Anaconda Prompt** (Start menu), not a plain Command Prompt or
  PowerShell — Anaconda's Python is already on the PATH there.
- Anaconda registers the command as `python` — **not** `python3`. If a
  command with `python3` fails or opens the Microsoft Store, just use
  `python` instead.
- Anaconda sidesteps the Windows "Python was not found" Store-alias problem
  entirely, since it puts its own Python on the PATH inside the prompt.
- `venv` works the same way inside Anaconda's base environment — no extra
  conda setup is needed.

### Alternative: python.org instead of Anaconda

Install Python 3.9+ from python.org and tick **"Add python.exe to PATH"** on
the very first installer screen — this is the step almost everyone misses.
Everything in Section 2 then works exactly as written, in a regular terminal.

If `python --version` says Python "was not found" and opens the Microsoft
Store, that's Windows' stub `python.exe` hijacking the command. Fix it under
**Settings → Apps → Advanced app settings → App execution aliases** by turning
**off** the entries for `python.exe` and `python3.exe`, then reopen your
terminal.

---

## 7. Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `python` not found / opens Microsoft Store | Windows App Execution Alias intercepting the command | Use Anaconda Prompt, or see [Section 6](#6-anaconda--windows-notes) |
| Prompt doesn't show `(venv)` | The venv isn't activated in this window | Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux) from `backend/` |
| `'uvicorn' is not recognized...` | `pip install -r requirements.txt` didn't run (or didn't finish) inside the active venv | Re-run it, watch for errors, confirm `where pip` (Windows) or `which pip` (macOS/Linux) points inside `venv` |
| Visiting `127.0.0.1:8000` shows `{"detail":"Not Found"}` | Normal — there's no route at `/` | Use `/health` or `/docs` instead |
| Status shows `[ BACKEND UNREACHABLE ]` | Backend not running, or wrong port | Confirm `uvicorn` is running and `API_BASE` in `index.html` matches its port |
| Browser console shows a CORS error | Backend's CORS policy is too strict | `api.py` currently allows all origins (`allow_origins=["*"]`) for local dev — check it wasn't tightened |
| "A maximum of 3 row operations is allowed" | You added a 4th operation | The queue UI already caps this at 3 — this only fires if you're hitting the API directly |
| Matrix entry rejected | Non-numeric text in a cell | Only numbers and fractions (`3/2`, `-4`) are valid entries |

---

## 8. Where to go from here

- **Deploying the backend:** run `uvicorn api:app --host 0.0.0.0 --port 8000`
  behind a reverse proxy (nginx, Caddy) or on a platform like Render, Fly.io,
  or Railway.
- **Deploying the frontend:** it's static — any static host works (GitHub
  Pages, Netlify, Vercel, S3). Just remember to update `API_BASE`.
- **Locking down CORS:** once you know your frontend's real domain, change
  `allow_origins=["*"]` in `api.py` to `allow_origins=["https://your-frontend.com"]`.
- **Extending the math:** `matrix_backend.py` has no web dependencies at all —
  it's a plain Python library. You can import and test it directly, or reuse
  it in a CLI, notebook, or another API framework entirely.
