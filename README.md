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


# Full Guide — Row Operation

A complete reference for everything in this project: what it does, how it's built, every feature it has, and the correctness/security work behind it. For a short judge-facing pitch, see `DEMO_GUIDE.md` instead — this document is the exhaustive version.

---

## 1. What this is

Row Operation is a web app for learning and demonstrating **elementary row operations** — Scaling, Interchange, and Replacement — the three operations used to solve systems of linear equations by hand. You set up a matrix, queue up to three operations, and get a full step-by-step trace from the original matrix to the final result, with every value kept as an **exact fraction** (never a rounded decimal).

---

## 2. Architecture

```
Browser (index.html)  <--HTTP/JSON-->  FastAPI (api.py)  -->  Math engine (matrix_backend.py)
     UI + state              validation + routing            pure Python, no web code
```

| Piece | File | Responsibility |
|---|---|---|
| **Frontend** | `frontend/index.html` | One self-contained file — HTML, CSS, and JS, no build step, no framework. Owns all UI state and rendering. |
| **API** | `backend/api.py` | Thin FastAPI wrapper. Validates requests with Pydantic, calls the engine, serializes the response. Owns nothing about matrices itself. |
| **Engine** | `backend/matrix_backend.py` | The actual math. Zero web dependencies — usable from a CLI, a notebook, or a different framework entirely, unchanged. |

This separation means the engine is unit-testable on its own, the API is a pure trust boundary, and the frontend can be replaced without touching either backend file.

### Request lifecycle

1. User sets up a matrix and operations, clicks **RUN**.
2. Frontend sends one `POST /api/solve` with the matrix and operations as JSON.
3. Pydantic validates shape (types, ranges, 1–3 operations) — bad shape never reaches the engine, bounces back as `422`.
4. `matrix_backend.py` applies each operation in order with exact fraction arithmetic, recording before/after snapshots.
5. The API serializes the full trace back as JSON.
6. Frontend renders it: original matrix → each step (with per-cell arithmetic) → final matrix.

Stateless throughout — no session, no stored history, one request produces one complete answer.

---

## 3. Features

### Matrix setup
- Rows and columns adjustable from **1 to 24**, via `+`/`-` steppers **or typed directly**.
- Typed input is digit-only (letters stripped as you type) and the actual resize is deferred to blur/Enter — so typing "12" doesn't briefly resize to 1 row and wipe out rows 2+ before the second digit lands.
- **Reset button**, same size as the steppers, positioned beside Cols: restores the matrix to the default 3×4, clears every cell to `0`, clears any error, and resets the trace panel.

### Operation queue
- Up to **3 operations**, each one of:
  - **Scaling** — `R_i → k·R_i`, factor typed directly (supports negative/fraction/decimal).
  - **Interchange** — `R_i ↔ R_j`.
  - **Replacement** — `R_i → R_i + k·R_j`, with a `+`/`−` sign toggle and a separate magnitude field.
- **Row and Source Row are combo boxes**, not free-text fields — they only ever list `R1` through `R<n>`, where `n` is the matrix's current row count. Options update live on resize; if a row a queued operation points at no longer exists after shrinking the matrix, it's automatically clamped to the new highest valid row.
- Every numeric field (matrix cells, Value/Factor fields) filters keystrokes in real time to only what a signed whole number, decimal, or fraction can contain: digits, one leading `-`, and one `.` *or* one `/` (never both).

### Step-by-step trace
- Linear, scrollable log: **Original Matrix → Step 1 → Step 2 → Step 3 → Final Matrix**, all visible at once (no tabs to click through).
- Each step shows the operation in compact math notation (e.g. `R2 + 3/2R1 -> R2`, `2R2 -> R2`), with the changed row(s) outlined.
- Beside each step's matrix, a **COMPUTATION** panel shows the literal per-cell arithmetic that produced it — e.g. `-3 + 3/2×2 = 0` — built entirely from the actual before/after values, not re-derived or approximated.

### Visual design
- Dark, CRT-terminal aesthetic: monospace type, bracketed section headers, scanline overlay, phosphor-green palette.
- All text colors were checked against WCAG contrast ratios against the background (not eyeballed) — a color that measured 1.65:1 (functionally invisible) was found and replaced everywhere it was used as text.
- Matrix and result cells are uniform size (150px, verified via computed-style checks) and sized generously enough that realistic multi-step fraction values (e.g. `-1089/200`) can't visually overflow into a neighboring cell.

---

## 4. Mathematical correctness

The three operations were checked against the formal textbook definitions, not just "does the code run":

| Property checked | Result |
|---|---|
| Scaling requires a nonzero factor (textbook constraint) | Enforced — scaling by 0 is rejected |
| Replacement allows a zero factor (no such constraint exists for it) | Correctly allowed |
| Interchange/Replacement require two distinct rows | Enforced for both |
| **Reversibility** — every elementary operation must have an inverse (scale by 1/k, swap twice, replace by −k) | Verified exactly equal to the original matrix, zero floating-point drift (exact `Fraction` arithmetic) |
| **E·A equivalence** — applying an operation to A must equal left-multiplying by E (that same operation applied to the identity) | Verified exactly, for all three operation types |
| A full worked 3-variable system, solved via 3 Replacement operations then back-substituted by hand | Cross-checked against an independently implemented Cramer's Rule solver sharing no code with the engine — exact match, and the solution satisfies all 3 original equations |

---

## 5. Security & input hardening

The engine and API were deliberately adversarially tested — "how would I break this" — not just happy-path tested.

**Bugs found and fixed**, each reproduced before being fixed:

- A non-numeric factor (`"banana"`) leaked a raw `ValueError` past the API's error handling, crashing the live server with an unhandled `500`. Fixed by parsing factors through one function that always raises the library's own error type.
- `limit_denominator` was applied to *every* input type, silently rounding an exact user-entered fraction with a large denominator. Fixed to apply only to `float` input, where it exists to clean up binary-float noise.
- Constructing a `Matrix` directly with mismatched data (claiming 3 rows, holding 1) produced no error and corrupted silently. Fixed with shape validation in `__post_init__`.
- `RowOperationRequest` was mutable but cached its parsed factor — mutating `.factor` after first use silently returned the stale cached value. Fixed by freezing the dataclass.
- `to_dict()` returned internal list objects by reference; mutating the returned dict corrupted the source object's own state. Fixed by returning fresh copies.
- **No dimension cap existed in the engine itself** — only the API's Pydantic layer capped matrix size. Constructing a 2000×2000 matrix directly took 3.5 seconds and a multi-million-object allocation with nothing to stop it. Fixed with `MAX_MATRIX_DIMENSION = 200`, enforced in the engine, independent of whatever wraps it.
- No length cap existed on a single numeric string, so one absurdly long value in a JSON field could be sent unchecked. Fixed with `MAX_NUMERIC_STRING_LENGTH = 64`.
- **`Infinity`** as a matrix value or factor (e.g. the JSON number `1e400`) raised `OverflowError`, which wasn't in the caught-exceptions list — confirmed this crashed the live API with a `500`. Fixed by adding `OverflowError` everywhere a number is parsed.
- Constructing a `Matrix` with non-integer `rows`/`cols` (a string, `None`, a float) crashed with an unhandled `TypeError`. Fixed with an explicit type check (the API itself was never at risk here — Pydantic already rejects this — but direct library use had no protection).

**Confirmed safe** during the same testing pass: nested lists, `None`, `dict`, `complex` numbers, `"1/0"`, empty/whitespace strings, out-of-bounds and negative row numbers, malformed operation lists, and adversarial strings designed to trigger regex backtracking (none did — Python's `fractions` module regex is linear-time).

### Input limits, exactly

Every matrix entry and every operation factor accepts a **whole number**, a **decimal**, or a **fraction** — signed or unsigned. Each format has its own precise limit:

| Format | Example | Limit | Enforced by |
|---|---|---|---|
| **Whole number** | `-42` | Max 64 characters as typed; the underlying digits are capped at 4300 (Python's own built-in integer-conversion limit) | `MAX_NUMERIC_STRING_LENGTH` + Python runtime |
| **Decimal** | `-1.25` | Same 64-character cap. Internally converted to the *closest exact fraction with a denominator of 1,000,000 or less* — this is what turns a messy binary float like `0.1` into a clean `1/10` instead of an ugly near-equivalent | `limit_denominator(10**6)`, floats only |
| **Fraction** | `-3/2` | Same 64-character cap. Unlike decimals, a fraction typed as text is kept **exactly** — even a large denominator like `1/1234567` is preserved precisely, never simplified or rounded | `MAX_NUMERIC_STRING_LENGTH` |

Two things worth calling out if asked:

- **The 64-character cap exists purely as a safety limit**, not a mathematical one — nothing a person would ever type by hand needs anywhere near 64 characters. It exists to stop a client from sending one pathologically long string in a single field and making the server do real work before validation even gets a chance to reject it.
- **Decimals and fractions are treated differently on purpose.** A decimal came from a float, which is *already* an approximation at the hardware level — rounding it to the nearest "nice" fraction is a correction, not a loss of precision. A fraction typed as text (`"1/1234567"`) was never approximate to begin with, so it's preserved exactly, however large its denominator, right up to the 64-character limit.

---

## 6. Performance

Measured with `timeit`, not assumed:

| Change | Result |
|---|---|
| `Matrix.copy()`: `copy.deepcopy` → shallow per-row copy (safe because `Fraction` is immutable and operations always build new rows) | **60x faster** (52.5µs → 0.9µs on a 12×12 matrix) |
| `to_dict()`: `dataclasses.asdict()` → hand-written dict construction | **334x faster** (157µs → 0.47µs) — matters because this runs on every API response |
| Each operation's factor parsed once and cached, reused for both the math and the notation string | Avoids re-parsing the same string twice per operation |
| Matrix display formatting computed once per state instead of twice at every step boundary | Halves redundant string formatting during a run |
| **Combined effect**, full realistic request path, max matrix size | **2.9x faster end-to-end** (578µs → 201µs per request, ~1,730 → ~4,980 req/s single-core) |

One optimization was tried and **rejected** after measuring: caching fraction-to-string formatting with `functools.lru_cache` looked like a natural win (matrices are full of repeated `0`s and `1`s) but measured ~4x *slower* — the cache's own overhead cost more than CPython already pays to format a short string.

### Memory footprint — how a number actually sits in RAM

Every matrix value is a Python `Fraction`, and a `Fraction` is really two `int`s underneath (a numerator and a denominator) plus a small object wrapper. What that costs in real memory, measured with `sys.getsizeof`, not estimated:

| Object | Size |
|---|---|
| A small Python `int` (anything roughly under ~1 billion in magnitude) | **28 bytes** |
| A `Fraction`'s own object wrapper (before its two ints) | **48 bytes** |
| A short numeric string like `"3/2"` (used for API responses/display) | **44 bytes** |
| An empty Python list | 56 bytes, **+8 bytes per cell** (each list slot is just a pointer) |

So one typical small-value `Fraction` (numerator + denominator both small ints) costs roughly `48 + 28 + 28 = 104` bytes fully expanded — except in practice it's usually *less* than that, because of one CPython detail worth knowing:

**CPython caches every small integer from -5 to 256 as a shared singleton.** Confirmed directly: two separately created `Fraction(0, 1)` objects have `numerator is numerator` return `True` — they're pointing at the *exact same* `int` object in memory, not two copies. Since row reduction produces matrices full of `0`s, `1`s, and other small values, most of a reduced matrix's numbers cost only the 8-byte pointer to reference an `int` that already exists elsewhere in the process — not a fresh 28-byte allocation per cell.

**Real measured totals** (via a recursive size-walk that correctly accounts for that sharing, so nothing is double-counted):

| Matrix | All-zero (typical of a reduced matrix) | All distinct nonzero values |
|---|---|---|
| 3×3 (smallest useful size) | 840 bytes | — |
| 12×12 | 9.1 KB | — |
| **24×24 (UI's max size)** | 33.1 KB | 48.8 KB |
| **200×200 (engine's hard safety cap)** | 2.2 MB | — |

**A full request**, measured end-to-end with `tracemalloc` (matrix construction → all 3 operations applied → the full step trace built → serialized to the actual JSON string that goes out over the wire):

| Request | Peak memory | JSON response size |
|---|---|---|
| Default demo size (3×4, 3 operations) | 8.5 KB | 885 bytes |
| **Maximum UI size (24×24, 3 operations)** | **290.5 KB** | 31.5 KB |

Even at the absolute maximum size the UI allows, one full request peaks under 300 KB — trivial for any modern server, and consistent with the throughput numbers above (this is *why* ~4,980 requests/second single-core is achievable: there's simply very little memory pressure per request to begin with).

---

## 7. API reference (condensed — see `API_REFERENCE.md` for full detail)

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/api/limits` | GET | Reports `max_operations` and `max_dimension` |
| `/api/solve` | POST | Takes `{rows, cols, entries, operations}`, returns `{original_matrix, final_matrix, steps}` |

Every error comes back as a `400` with a single `detail` string (never a raw `500` for input problems) or a `422` for malformed request shape.

---

## 8. Project structure

```
row-reducer/
├── README.md            ← architecture overview
├── TUTORIAL.md          ← setup instructions (incl. Windows notes)
├── API_REFERENCE.md     ← full endpoint documentation
├── DEMO_GUIDE.md        ← short judge-facing pitch/demo script
├── FULL_GUIDE.md         ← this file
├── backend/
│   ├── matrix_backend.py   ← math engine
│   ├── api.py              ← FastAPI wrapper
│   └── requirements.txt
└── frontend/
    └── index.html           ← the entire UI
```

## 9. Setup

Full instructions, including Windows-specific gotchas, are in `TUTORIAL.md`. Short version:

```bash
cd backend
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Then open `frontend/index.html` in a browser.

### What each command actually does

| Command | What it does | Why it's needed |
|---|---|---|
| `cd backend` | Moves the terminal into the folder holding `api.py`, `matrix_backend.py`, and `requirements.txt` | Every command after this is relative to the current folder — it has to happen first |
| `python -m venv venv` | Creates a private, self-contained copy of Python in a new `venv/` folder | Keeps this project's dependencies isolated from system Python, so they can't clash with what another project needs |
| `source venv/bin/activate` (`venv\Scripts\activate` on Windows) | Temporarily rewrites the shell's `PATH` so `python`/`pip` point at the copies inside `venv/` instead of the system ones | Everything installed afterward lands in the isolated environment, not globally — confirmed by `(venv)` appearing in the prompt |
| `pip install -r requirements.txt` | Installs exactly `fastapi`, `uvicorn`, and `pydantic` (the file's contents) into the now-active venv | These are the only three packages the backend needs; installing them elsewhere would defeat the point of the venv |
| `uvicorn api:app --reload --port 8000` | Starts the server: `uvicorn` is the program that actually runs a FastAPI app; `api:app` means "the `app` variable inside `api.py`" (`app = FastAPI(...)`, line 29); `--reload` restarts on every file save (dev only); `--port 8000` is the port to listen on | `--port 8000` has to match the frontend's hardcoded `API_BASE` (`http://127.0.0.1:8000`) or the browser can't find the server at all |

Opening `frontend/index.html` needs no command — it's a static file, so double-clicking it (or dragging it into a browser) is enough. It immediately starts polling the server started above.

---

## 10. Key design decisions

- **Exact fractions over floats, everywhere.** The entire point of the tool is showing correct row-reduction work; floating-point rounding would undermine that.
- **Limits enforced twice, independently.** The 3-operation cap and matrix-size cap exist in both the API layer (UX-driven, tighter) and the engine itself (safety backstop, looser) — so neither can be bypassed by skipping the other.
- **The engine knows nothing about the web.** No HTTP, no JSON, no FastAPI import in `matrix_backend.py` — it's reusable anywhere plain Python runs.
- **No build tooling anywhere.** One HTML file, two Python files. Nothing to compile, bundle, or configure.

---

## 11. Frontend script reference

`index.html` has one global state object and roughly 20 functions. No framework, no build step — everything below is plain JavaScript reading from or writing to a single object called `state`.

### State

```js
const state = { rows, cols, entries, operations };
```

One object holding the entire app's current condition — matrix size, its values, and the operation queue. Every function either reads `state` to render the UI or writes to `state` in response to a click/keystroke. There's no state-management library; the object itself *is* the state management, which is appropriate at this app's size.

### Startup

| Function | What it does |
|---|---|
| `checkHealth()` | Calls `GET /health` once on page load, flips the status badge to ONLINE/UNREACHABLE. Runs once at load, not on a timer. |

### Matrix grid

| Function | What it does |
|---|---|
| `resizeEntries()` | Rebuilds `state.entries` to match the current rows/cols. Keeps existing values where they still fit, fills new cells with `"0"`. |
| `sanitizeNumericInput(raw)` | Character-by-character filter: keeps only digits, one leading `-`, and one `.`/`/`. Pure function (string in, string out) — reused identically for matrix cells and the operation Value/Factor fields. |
| `renderMatrixGrid()` | Rebuilds every `<input>` in the grid from `state.entries`. Each input sanitizes on every keystroke and writes straight back into `state.entries[r][c]`. |

### Rows/Cols controls

| Function | What it does |
|---|---|
| `[data-dim]` click handler | The `+`/`-` stepper buttons. Reads which was clicked from its own `data-dim`/`data-dir` attributes, clamps to 1–24, re-renders. |
| `wireDimensionTyping(inputId, dim)` | Makes Rows/Cols typeable. Filters to digits-only on every keystroke, but defers the actual resize to `blur`/`Enter` (via its inner `commit()`) — so typing "12" doesn't resize to 1 row first and wipe data before the second digit lands. |
| `resetMatrixBtn` click handler | Inline, unnamed. Resets `state` to the 3×4 zero-filled default, re-renders the grid and operations panel, clears any error, resets the trace panel's HTML. |

### Operation queue

| Function | What it does |
|---|---|
| `rowOptionsHtml(idx, field, selectedValue)` | Builds a dropdown's `<option>` list, `R1` through `R<state.rows>` — generated fresh from the live row count every render, which is *why* an invalid row can never be selected. |
| `opFieldsHtml(op, idx)` | Picks which fields an operation card needs based on its type (Scaling: Row+Factor; Interchange: Row+With Row; Replacement: Row+Source Row+Sign+Value). Clamps `op.row`/`op.row_b` back into range first if the matrix shrank since they were set. |
| `renderOps()` | Rebuilds every operation card from `state.operations`, then wires five separate listeners: op-type dropdown, row/row_b dropdowns, sign/operator toggles, magnitude/factor text inputs, and each card's remove button. Rebuild-then-rewire every call, not incremental patching. |
| `updateAddOpState()` | One line — disables "+ Add operation" once there are 3 operations. |
| `addOpBtn` click handler | Pushes a default Scaling operation onto `state.operations`, re-renders. |

### Running and showing results

| Function | What it does |
|---|---|
| `showError(msg)` / `clearError()` | Toggle the error banner's text and visibility. Centralized so every error path looks identical. |
| `computeFactor(op)` | Converts the UI's split representation (sign toggle + magnitude, Replacement only) into the single signed string the backend expects (`sign:"-", magnitude:"2"` → `"-2"`). Scaling passes its factor straight through. |
| `runOperations()` | The actual submit: builds the request body from `state`, `fetch()`s `POST /api/solve`, calls `renderResults()` on success or `showError()` on failure — both an HTTP-level error and a network failure (server unreachable) are handled separately. |
| `diffRows(before, after)` | Compares two matrices row-by-row (via JSON string comparison — cheap, since rows are small string arrays) to find which rows to highlight red. |
| `renderMatrixDisplay(matrix, changedRows)` | Builds the grid of `.cell` divs for a result matrix, marking changed rows. |
| `splitSign(factorStr)` | Pulls the sign off a factor string (`"-3/2"` → `{sign:"-", abs:"3/2"}`) so computation lines read as natural subtraction instead of `"+ -3/2"`. |
| `renderComputationPanel(op, matrixBefore, matrixAfter)` | Builds the per-cell arithmetic panel beside a step. Returns `null` when there's no operation to explain (the Original/Final blocks). |
| `renderMatrixWithComputation(...)` | Glues a matrix display and its computation panel into one side-by-side flex wrapper. |
| `renderResults(data, operations)` | Final assembly: builds the Original block, loops `data.steps` pairing each with its submitted operation to build a Step block, then builds the Final block — this is what actually populates the trace panel after a successful run. |

---

## 12. API layer reference (`api.py`)

The whole file is 79 lines. Every piece has one specific job.

| Piece | What it does |
|---|---|
| Module docstring | States the file's one rule up front: this is the only place that knows HTTP exists. Imports from `matrix_backend` (`Matrix`, `RowOperationEngine`, `RowOperationRequest`, `RowOperationType`, `MatrixError`, `MAX_OPERATIONS`) are the entire surface this file touches — it never reaches into the engine's internals. |
| `MAX_DIMENSION = 24` | A local constant, deliberately smaller than the engine's own `MAX_MATRIX_DIMENSION = 200`. One is a UX choice (keeps the grid usable on screen), the other a safety backstop — two independent limits, not one duplicated. |
| `app = FastAPI(...)` | Creates the application object — the exact `app` that `uvicorn api:app` looks for by name. |
| `app.add_middleware(CORSMiddleware, ...)` | CORS is a browser rule: by default a page can't `fetch()` a server on a different origin than itself. Since `index.html` is opened as a local file or a different port than the API, this tells the browser "any origin may call this API." Flagged in its own comment as dev-only, to tighten before deploying. |
| `NumberIn = Union[int, float, str]` | A type alias (not a class) defining what counts as "a valid raw number" for Pydantic — a plain number, or a string like `"3/2"` for exact fractions. |
| `class OperationIn(BaseModel)` | Shape of one operation in the incoming JSON. `Field(..., ge=1)` means required and ≥ 1 — this is where a negative or zero row number gets rejected before any of *your* code runs. `row_b`/`factor` are `Optional` since not every operation type needs them. |
| `class SolveRequest(BaseModel)` | Shape of the whole request body. `le=MAX_DIMENSION` caps rows/cols at 24. `max_items=MAX_OPERATIONS, min_items=1` caps operations at 1–3 — the *first* of the two independent enforcements of that limit (the second lives inside `RowOperationEngine.run()` itself). |
| `GET /health` → `health()` | No logic at all — just confirms the server is up. What the frontend's status badge polls. |
| `GET /api/limits` → `limits()` | Reports `max_operations`/`max_dimension` as JSON, so a client could discover them at runtime instead of hardcoding — though the current frontend doesn't call this yet. |
| `POST /api/solve` → `solve(request)` | The real work, four lines: (1) `Matrix.from_entries(...)` converts the validated request into an exact-fraction `Matrix`; (2) a list comprehension translates each Pydantic `OperationIn` into the engine's own `RowOperationRequest`; (3) `RowOperationEngine(matrix).run(ops)` does the actual reduction; (4) `result.to_dict()` — FastAPI auto-serializes whatever a route returns, so this is the last touchpoint before the JSON response goes out. |
| `except MatrixError as e: raise HTTPException(400, str(e))` | The single error-handling line for the whole file. Every domain error the engine can raise (bad row, zero factor, malformed number, oversized matrix) inherits from `MatrixError`, so one `except` catches all of them uniformly and turns each into a clean `400` with that error's own message. Anything that *isn't* a `MatrixError` — a genuine bug — is deliberately left uncaught here and surfaces as a real `500`, since that's not a user-input problem to hide. |

---

## 13. Math engine reference (`matrix_backend.py`)

The module docstring itself is a running engineering log — it states the file's four responsibilities up front, then documents every optimization tried (including the one rejected after measuring), every bug found and fixed, and every security hole closed. What follows is the code itself.

### Module-level constants

| Constant | Value | Purpose |
|---|---|---|
| `NumericInput` | `Union[int, float, Fraction, str]` | What counts as "a valid raw number" anywhere in this file. Named to avoid colliding with the standard library's own `numbers.Number`. |
| `MAX_OPERATIONS` | `3` | Enforced here, independently of the API's own copy of this limit. |
| `MAX_MATRIX_DIMENSION` | `200` | The engine's own hard size cap — a safety backstop regardless of whatever wraps this file (the API's tighter `24` is a separate, independent limit). |
| `MAX_NUMERIC_STRING_LENGTH` | `64` | Rejects an absurdly long numeric string before it's ever parsed. |

### Module-level helpers

| Function | What it does |
|---|---|
| `_to_fraction(raw_value)` | The actual number parser — converts anything in `NumericInput` into an exact `Fraction`. The one real subtlety: `limit_denominator` is applied only to `float` input, since a float like `0.1` is already an approximation at the hardware level (cleaning it into `1/10` is a correction), while a fraction string like `"1/1234567"` was never approximate and is preserved exactly. Also enforces the 64-character length cap before `Fraction()` itself runs. |
| `_parse_fraction_strict(raw_value)` | Thin wrapper: calls `_to_fraction`, converts any failure (`ValueError`/`ZeroDivisionError`/`TypeError`/`OverflowError`) into this library's own `RowOperationError`. Every place that parses a number goes through this one function, so there's exactly one place deciding what "bad number" looks like as an error. |

### `Matrix` — the data itself

| Method | What it does |
|---|---|
| `__post_init__` | Runs automatically right after construction. Checks `rows`/`cols` are actually integers, positive, and within `MAX_MATRIX_DIMENSION` — then either fills a fresh zero matrix or validates supplied `data` really is the declared shape. Runs no matter *how* a `Matrix` gets built. |
| `from_entries(rows, cols, entries)` *(classmethod)* | The actual entry point client code calls. Converts every raw value via `_to_fraction`, checking shape and the size cap *before* touching any cell — an oversized request is rejected in roughly constant time instead of after doing the conversion work. |
| `copy()` | Returns an independent `Matrix`. Only copies each row's list, not the numbers inside — safe because `Fraction` is immutable and every row operation below builds a brand-new row rather than mutating one in place. |
| `_check_row_index(row_idx)` | One-line bounds check, called by all three row operations below. |
| `_format_fraction(value)` *(staticmethod)* | Turns a `Fraction` into display text — `"3"` for a whole number, `"1/2"` for a fraction, never `"3/1"`. |
| `to_display_rows()` | Runs `_format_fraction` over the whole matrix — becomes the JSON strings the frontend renders. |
| `scale_row(row, factor)` | `R_row → factor × R_row`. Rejects a zero factor, since scaling by zero would destroy information — excluded from the textbook definition of the operation for exactly that reason. |
| `interchange_rows(row_a, row_b)` | `R_a ↔ R_b`. Rejects swapping a row with itself. |
| `replace_row(target_row, source_row, factor)` | `R_target → R_target + factor × R_source` — the operation that actually eliminates variables. A negative factor is how "subtraction" happens; there's no separate subtract operation. |

### `RowOperationRequest` — one queued operation

A **frozen** dataclass — deliberately, because `parsed_factor` is a `@cached_property` that remembers its answer the first time it's read. If `factor` could change after creation, that cached answer would silently go stale; freezing the object rules the bug out structurally rather than relying on nobody triggering it.

| Member | What it does |
|---|---|
| `parsed_factor` | The factor as an exact `Fraction`, computed once and reused by both the actual arithmetic and the notation string below — avoids parsing the same string twice. |
| `describe()` | Builds the notation shown in the trace (`"3/2R1 -> R1"`, `"R2 + (-1/2R1) -> R2"`, `"R1 <-> R2"`) — a negative replacement factor gets wrapped in parentheses. |
| `_format_factor()` | Same display formatting as `Matrix._format_fraction`, applied to `parsed_factor`. |

### `OperationStep` / `RowOperationResult` — the output shape

- **`OperationStep`** — one operation's before/after snapshot plus its description. The trace is just a list of these.
- **`RowOperationResult`** — the whole run's outcome (starting matrix, ending matrix, every step). Its `to_dict()` hand-builds the dictionary instead of using `dataclasses.asdict()` (334x faster, measured, and this runs on every request), and returns *fresh copies* of every row list rather than the object's own internal ones — closing an aliasing bug where editing the returned dict could otherwise corrupt the source object. `to_json()` is just `to_dict()` piped through `json.dumps`.

### `RowOperationEngine` — runs everything

| Method | What it does |
|---|---|
| `__init__(matrix)` | Snapshots the given matrix via `.copy()`, so changes to the caller's own object afterward can't retroactively affect a run already using it. |
| `run(operations)` | The main entry point. Validates the operation count (1–3, enforced here independently of the API), applies each in order on a working copy, recording a before/after `OperationStep` for each — reusing the previous step's "after" as the next step's "before" instead of reformatting the same state twice. If anything fails partway, the original matrix is never touched. |
| `_apply(matrix, op)` *(staticmethod)* | Translates one `RowOperationRequest` into the matching `Matrix` method call, converting its 1-indexed rows to 0-indexed positions, and checking each operation type actually has the fields it needs before calling in. |

### CLI helpers & demo

`print_matrix`/`print_result` are plain-console pretty-printers, used only by the `if __name__ == "__main__":` block at the bottom of the file — a runnable demo of the exact 3-operation reduction used throughout this project, confirming the module works completely standalone with no API involved.
