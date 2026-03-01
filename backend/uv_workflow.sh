#!/bin/bash
# Complete uv workflow for Dyadic Analyzer backend
# Source this file or run individual commands

set -e

echo "🚀 Dyadic Analyzer - uv Workflow"
echo "================================"

# 1. Create virtual environment
echo "📦 Creating virtual environment..."
uv venv .venv

# 2. Activate venv
echo "✨ Activating venv..."
source .venv/bin/activate

# 3. Install dependencies
echo "⚡ Installing dependencies (this is fast!)..."
uv pip install -e .

# 4. Generate lock file for reproducibility
echo "🔒 Generating lock file..."
uv pip compile pyproject.toml -o uv.lock

# 5. Setup environment
echo "⚙️  Setting up .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✅ Created .env (edit with your API keys)"
else
    echo "   ℹ️  .env already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the server:"
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "To use the lock file in CI/CD:"
echo "  uv pip install -r uv.lock"
echo ""
