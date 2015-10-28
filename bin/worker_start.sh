#!/bin/bash

# Name of the application
NAME="himawari_celery_worker"

# Project directory (contains the actual application that we're going to run)
SERVERDIR=/home/jeremy/servers/himawari_bot/

# Virtual environment directory
VENVDIR=/home/jeremy/Envs/himawari

# the user and group the program should run as
USER=jeremy
GROUP=jeremy

NUM_WORKERS=1

echo "Starting celery worker as `whoami`"

# Activate the virtual environment
source $VENVDIR/bin/activate

# Append the server directory to our python path environment variable.
export PYTHONPATH=$SERVERDIR:$PYTHONPATH

# Programs meant to be run under supervisor should not daemonize themselves
# (do not use --daemon). So we'll cd to our server directory and then
# execute the program using the virtualenv's version of python.
cd $SERVERDIR

exec celery -A celery_conf worker -Q himawari -l INFO -n himawari_bot_worker