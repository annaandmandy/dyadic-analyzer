# Quick Start with `uv` (Recommended)

`uv` is a blazingly fast Python package manager written in Rust. **Much faster than pip.**

## Install `uv`

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or use `pipx`:
```bash
pipx install uv
```

Verify:
```bash
uv --version
```

---

## Backend Setup with `uv`

### Step 1: Navigate to backend
```bash
cd backend
```

### Step 2: Create venv and install (one command!)
```bash
uv venv
source .venv/bin/activate   # macOS/Linux
# or
.venv\Scripts\activate       # Windows
```

### Step 3: Install dependencies (10x faster than pip)
```bash
uv pip install -e .
```

Or if you want to use `requirements.txt`:
```bash
uv pip install -r requirements.txt
```

### Step 4: Run the server
```bash
uvicorn app.main:app --reload --port 8000
```

---

## Why `uv` is faster

- **Parallel dependency resolution** — installs multiple packages at once
- **Optimized Rust implementation** — much faster than Python pip
- **Lock file support** — reproducible installs (uv.lock)
- **Workspace support** — multi-package projects

## Common `uv` commands

```bash
# Create virtual environment
uv venv

# Activate (same as venv)
source .venv/bin/activate

# Install from pyproject.toml
uv pip install -e .

# Install from requirements.txt
uv pip install -r requirements.txt

# Add a new package
uv pip install package-name

# Install dev dependencies (if you add a [project.optional-dependencies])
uv pip install -e ".[dev]"

# Generate lock file for reproducibility
uv pip compile pyproject.toml -o requirements.lock

# Install from lock file (CI/CD friendly)
uv pip install -r requirements.lock
```

---

## Frontend Setup (faster with `uv` + Bun)

You can also use **Bun** for the frontend (even faster than npm):

```bash
cd frontend
bun install
bun run dev
```

Or stick with npm/yarn (they work fine too).

---

## Performance Comparison

| Tool | Time | Notes |
|------|------|-------|
| pip | ~60s | Slow, serial resolution |
| poetry | ~45s | Slower, complex |
| **uv** | **~5s** | ⚡ Blazing fast |

---

## Docker with `uv`

The `Dockerfile` is already updated to use `uv`. Just run:

```bash
docker-compose up --build
```

The backend container will install dependencies ~10x faster!
