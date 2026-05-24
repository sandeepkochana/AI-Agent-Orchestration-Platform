#!/usr/bin/env bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   AI Agent Orchestration Platform — Setup            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Check prerequisites ───────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "❌  python3 is required."; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "❌  node is required (v18+)."; exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "❌  npm is required."; exit 1; }

echo "✅  Prerequisites OK"

# ── Backend ───────────────────────────────────────────────────────────────────
echo ""
echo "📦  Setting up backend..."
cd backend

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f ".env" ]; then
  cp ../.env.example .env
  echo ""
  echo "⚠️   Created backend/.env from .env.example"
  echo "    Please fill in your OPENAI_API_KEY (and optionally TELEGRAM_BOT_TOKEN) before starting."
fi

cd ..

# ── Frontend ──────────────────────────────────────────────────────────────────
echo ""
echo "📦  Setting up frontend..."
cd frontend
npm install --silent
cd ..

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  Setup complete!                                 ║"
echo "║                                                      ║"
echo "║  To start the platform:                              ║"
echo "║                                                      ║"
echo "║  Terminal 1 — Backend:                               ║"
echo "║    cd backend && source .venv/bin/activate           ║"
echo "║    uvicorn main:app --reload --port 8000             ║"
echo "║                                                      ║"
echo "║  Terminal 2 — Frontend:                              ║"
echo "║    cd frontend && npm run dev                        ║"
echo "║                                                      ║"
echo "║  Open: http://localhost:3000                         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
