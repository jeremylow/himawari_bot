#!/bin/bash

SERVERDIR=/home/jeremy/servers/himawari_bot
VENVDIR=/home/jeremy/Envs/himawari
USER=jeremy # the user to run as
GROUP=jeremy # the group to run as

echo "Starting celery beat as `whoami`"

# Activate the virtual environment
cd $SERVERDIR
source $VENVDIR/bin/activate
export PYTHONPATH=$SERVERDIR:$PYTHONPATH

# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec celery -A celery_conf beat -l INFO -n himawari_bot_beat