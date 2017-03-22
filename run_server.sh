#!/bin/bash

gunicorn IOTApp:app -p venv/.gunicorn_pid -b 127.0.0.1:8000 -D
