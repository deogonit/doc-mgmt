#!/bin/bash

gunicorn app.run:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind "0.0.0.0:8000" --access-logfile -
