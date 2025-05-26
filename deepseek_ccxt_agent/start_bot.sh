#!/bin/bash
source venv/bin/activate
screen -dmS deepseek_bot uvicorn app.main:app --host 0.0.0.0 --port 8000
