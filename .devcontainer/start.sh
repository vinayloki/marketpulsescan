#!/bin/bash
echo "Starting MarketPulse Platform..."

# Start the FastAPI backend in the background
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
echo "✅ Backend API started on port 8000"

# Start the Vite React frontend in the background
cd frontend
nohup npm run dev -- --host 0.0.0.0 --port 5173 > frontend.log 2>&1 &
echo "✅ Frontend UI started on port 5173"

echo ""
echo "🚀 Everything is running! You can now click the forwarded ports in VS Code to see the app."
