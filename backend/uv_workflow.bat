@echo off
REM Complete uv workflow for Dyadic Analyzer backend (Windows)

echo 🚀 Dyadic Analyzer - uv Workflow (Windows)
echo ========================================

REM 1. Create virtual environment
echo 📦 Creating virtual environment...
uv venv .venv

REM 2. Activate venv
echo ✨ Activating venv...
call .venv\Scripts\activate.bat

REM 3. Install dependencies
echo ⚡ Installing dependencies (this is fast!)...
uv pip install -e .

REM 4. Generate lock file for reproducibility
echo 🔒 Generating lock file...
uv pip compile pyproject.toml -o uv.lock

REM 5. Setup environment
echo ⚙️  Setting up .env...
if not exist .env (
    copy .env.example .env
    echo    ✅ Created .env (edit with your API keys)
) else (
    echo    ℹ️  .env already exists
)

echo.
echo ✅ Setup complete!
echo.
echo To run the server:
echo   .venv\Scripts\activate.bat
echo   uvicorn app.main:app --reload --port 8000
echo.
echo To use the lock file in CI/CD:
echo   uv pip install -r uv.lock
echo.
pause
