# Row Operation — Setup Tutorial

This project has two independent pieces:

```
comp3/
├── backend/
│   ├── matrix_backend.py   ← core matrix engine (no web code)
│   ├── api.py              ← FastAPI wrapper, exposes it over HTTP
│   └── requirements.txt
└── frontend/
    └── index.html           ← self-contained UI (HTML + CSS + JS, no build step)
```

The frontend is a single static HTML file — no npm, no bundler. It talks to the
backend over HTTP, so you just need the backend running first.

---

## 1. Prerequisites

- Python 3.9+ — either a plain install from python.org, **or** Anaconda (both
  work fine; see the Windows notes below if you hit trouble)
- A modern browser (Chrome, Firefox, Edge, Safari)

Check your Python version:

```
python --version
```

> **Windows users:** see [Section 6](#6-windows-notes) first if this command
> tells you Python "was not found" and offers to open the Microsoft Store —
> that's a common gotcha, not a real error, and it's a two-minute fix.

---

## 2. Set up the backend

**Step 1 — Open a terminal in the `backend/` folder:**

```
cd comp3/backend
```

**Step 2 — Create a virtual environment (recommended):**

```
python -m venv venv
```

Activate it:

```
# macOS/Linux
source venv/bin/activate

# Windows (Command Prompt or PowerShell)
venv\Scripts\activate

# Windows (Anaconda Prompt) — venv still works the same way inside conda's base env
venv\Scripts\activate
```

Your prompt should now show `(venv)` at the start of the line.

**Step 3 — Install dependencies:**

```
pip install -r requirements.txt
```

Let this fully finish — it should pull in `fastapi`, `uvicorn`, `pydantic`,
and their sub-dependencies. If `uvicorn` isn't found in the next step, this
is almost always why: come back and re-run this install.

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

```
cd row-reducer/frontend
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

## 6. Windows notes

### "Python was not found" / redirects to the Microsoft Store

Windows ships a stub `python.exe` that hijacks the command and offers to
install from the Store instead of running your real Python. Fix:

1. Open **Settings → Apps → Advanced app settings → App execution aliases**.
2. Turn **off** the two entries for `python.exe` and `python3.exe`.
3. Close and reopen your terminal, then re-check `python --version`.

If you install a fresh Python from python.org instead, make sure to check
**"Add python.exe to PATH"** on the very first installer screen — this is the
step almost everyone misses.

### Using Anaconda instead

Anaconda works fine and sidesteps the Store-alias issue entirely, since it
adds its own **Anaconda Prompt** with Python already on its PATH.

- Use **Anaconda Prompt** (Start menu), not a plain Command Prompt.
- Anaconda only registers the command as `python` — **not** `python3`. If a
  command with `python3` fails with the same Store-redirect message, that's
  why; just use `python` instead.
- Optional: keep this project isolated from your other conda environments:
  ```
  conda create -n rowop python=3.11
  conda activate rowop
  ```
- From there, everything in Section 2 works exactly as written (`python -m venv venv`,
  `pip install -r requirements.txt`, `uvicorn api:app --reload --port 8000`).

---

## 7. Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `python` not found / opens Microsoft Store | Windows App Execution Alias intercepting the command | See [Section 6](#6-windows-notes) |
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
