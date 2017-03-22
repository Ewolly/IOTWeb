#!/bin/bash

kill $(cat /var/www/IOTWeb/venv/.gunicorn_pid)
