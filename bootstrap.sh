#!/bin/bash

mkdir hires
mkdir lowres
mkdir videos

pip3 install -r /data/himawari_bot/requirements.txt

ln -s himawari_cron /etc/cron.d/himawari_cron
chmod 0644 /etc/cron.d/himawari_cron
