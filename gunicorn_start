#!/bin/bash

NAME=csss-site
DIR=/home/csss-site/csss-site-backend/src
USER=csss-site
GROUP=csss-site
WORKERS=2 # TODO: should we increase this?
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV=/home/csss-site/.venv/bin/activate
BIND=unix:$DIR/run/gunicorn.sock
LOG_LEVEL=error

cd $DIR
source $VENV

exec gunicorn main:app \
  --name $NAME \
  --workers $WORKERS \
  --worker-class $WORKER_CLASS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=-
