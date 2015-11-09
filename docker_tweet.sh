#!/bin/sh

docker run -d -v /home/ubuntu/apps/himawari/config.py:/data/himawari_bot/config.py -v /home/ubuntu/apps/himawari/hires.log:/data/himawari_bot/hires.log -v /home/ubuntu/apps/himawari/hires:/data/himawari_bot/hires jeremylow/himawari2:latest cron -f
