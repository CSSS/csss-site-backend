#!/bin/bash

NAME=csss-site
DIR= # fill this out yourself
USER= # fill this out yourself
GROUP= # fill this out yourself
WORKERS=2 # TODO: should we increase this?
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV= # fill this out yourself
BIND= # e.g., unix:/var/www/gunicorn.sock
LOG_LEVEL=error

cd $DIR
source $VENV

gunicorn main:app \
  --name $NAME \
  --workers $WORKERS \
  --worker-class $WORKER_CLASS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=-
