#!/bin/bash
set -e

# Move into backend where main.py lives
cd backend

# Start FastAPI with uvicorn, using Railway's PORT env
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
