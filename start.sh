#!/bin/bash
echo "=========================================="
echo "  VoltIQ - Energy Discovery Platform"
echo "=========================================="
echo ""

echo "Starting Flask backend..."
cd Backend || exit 1
pip install flask flask-cors -q
python app.py &
BACKEND_PID=$!
echo "Backend running at http://127.0.0.1:5000 (PID: $BACKEND_PID)"

cd .. || exit 1

echo ""
echo "Starting frontend server..."
cd Frontend || exit 1
python -m http.server 8080 &
FRONTEND_PID=$!
echo "Frontend running at http://127.0.0.1:8080 (PID: $FRONTEND_PID)"

echo ""
echo "Open http://127.0.0.1:8080 in your browser"
echo "Press Ctrl+C to stop both servers"

wait
