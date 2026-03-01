# `uv` Cheat Sheet for Dyadic Analyzer

## Installation

**One-liner for macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or via pipx:**
```bash
pipx install uv
```

---

## Getting Started (30 seconds)

```bash
cd backend

# Automated setup (macOS/Linux)
bash uv_workflow.sh

# Or manual steps:
uv venv
source .venv/bin/activate      # or: .venv\Scripts\activate (Windows)
uv pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Windows users:** Run `uv_workflow.bat` instead.

---

## Common Commands

| Task | Command |
|------|---------|
| Create venv | `uv venv` |
| Activate (macOS/Linux) | `source .venv/bin/activate` |
| Activate (Windows) | `.venv\Scripts\activate` |
| Install project deps | `uv pip install -e .` |
| Install from requirements.txt | `uv pip install -r requirements.txt` |
| Add a package | `uv pip install package-name` |
| Remove a package | `uv pip uninstall package-name` |
| List installed packages | `uv pip list` |
| Freeze to requirements.txt | `uv pip freeze > requirements.txt` |
| Generate lock file | `uv pip compile pyproject.toml -o uv.lock` |
| Install from lock file | `uv pip install -r uv.lock` |
| Update all packages | `uv pip install --upgrade -e .` |
| Sync exact versions | `uv pip sync uv.lock` |

---

## Why `uv` is Awesome

✅ **10x faster** than pip
✅ **Parallel dependency resolution**
✅ **Reproducible installs** with lock files
✅ **Pure Rust** — no Python overhead
✅ **Drop-in pip replacement** — same syntax
✅ **Works with pyproject.toml** — modern Python packaging

### Speed Comparison
```
pip:    ~60 seconds
uv:     ~6 seconds  (10x faster!)
```

---

## Reproducible Builds with Lock Files

Perfect for CI/CD:

```bash
# Generate lock file once
uv pip compile pyproject.toml -o uv.lock

# Install exact versions in CI
uv pip install -r uv.lock
```

This ensures:
- Exact same versions across machines
- Faster CI/CD (no resolution step)
- No surprises from dependency updates

---

## Docker Builds (Already Optimized!)

The `Dockerfile` now uses `uv`. Docker builds will be **much faster**.

```bash
docker-compose up --build
```

The backend image will install dependencies in ~10 seconds instead of ~60 seconds!

---

## Tips & Tricks

### 1. Skip venv activation in scripts
```bash
uv run uvicorn app.main:app --reload
```
(uv automatically activates the venv)

### 2. Run Python directly in venv
```bash
uv run python -c "import app; print('works!')"
```

### 3. Install and run in one command
```bash
uv pip install -e . && uv run uvicorn app.main:app --reload
```

### 4. Check venv location
```bash
which python    # macOS/Linux
where python    # Windows
```

### 5. Remove venv (when updating)
```bash
rm -rf .venv
uv venv
uv pip install -e .
```

---

## Environment Variables

Create `.env` from the template:
```bash
cp .env.example .env
```

Edit with your API keys:
```env
DYADIC_OPENAI_API_KEY=sk-...
DYADIC_ELEVENLABS_API_KEY=...
```

---

## Troubleshooting

**Problem:** `uv: command not found`
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or check your PATH is updated
```

**Problem:** `No module named 'app'`
```bash
# Make sure you're in the backend directory
cd backend
uv pip install -e .
```

**Problem:** Want to go back to pip?
```bash
# uv.lock can be used with pip
pip install -r uv.lock

# Or regenerate requirements.txt
uv pip freeze > requirements.txt
```

---

## Resources

- 📖 [uv Documentation](https://docs.astral.sh/uv/)
- 🔗 [GitHub: astral-sh/uv](https://github.com/astral-sh/uv)
- 💬 [Discord](https://discord.gg/astral-sh)

---

**Happy fast installing! ⚡**
