#!/bin/bash
apt-get update -y && apt-get install -y ffmpeg
gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 api.app:app
