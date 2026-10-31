#!/usr/bin/env bash
# Quick local server to preview the GitHub Pages site
PORT=8000
echo "=========================================================="
echo " Starting StaffHunt Local Web Server on http://localhost:$PORT"
echo " Press Ctrl+C to stop"
echo "=========================================================="
python3 -m http.server $PORT
