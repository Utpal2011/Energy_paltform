#!/bin/bash
echo "=========================================="
echo "  VoltIQ - Energy Discovery Platform"
echo "=========================================="
echo ""

cd Backend || exit 1
pip install flask flask-cors -q

echo "Open http://127.0.0.1:5000 in your browser"
echo "Press Ctrl+C to stop the server"
echo ""

# Flask serves both the API and the Frontend folder.
python app.py
