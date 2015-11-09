FROM armv7/armhf-ubuntu:15.04
MAINTAINER Jeremy Low <jeremy@hrhs.co.uk>

ENV TERM linux

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y build-essential \
    software-properties-common \
    python3 \
    python3-dev \
    python3-pip \
    python-virtualenv \
    imagemagick \
    git \
    ffmpeg \
    libgeos-dev \
    zlib1g-dev \
    libjpeg-dev

RUN apt-get install -y tree vim

RUN pip3 install amqp==1.4.7 \
    anyjson==0.3.3 \
    beautifulsoup4==4.4.1 \
    billiard==3.3.0.21 \
    celery==3.1.19 \
    kombu==3.0.29 \
    oauthlib==1.0.3 \
    pillow==3.0.0 \
    pyproj==1.9.4 \
    pytz==2015.7 \
    requests-oauthlib==0.5.0 \
    requests==2.8.1 \
    shapely==1.5.13 \
    six==1.10.0 \
    tweepy==3.4.0 \
    twython==3.3.0

WORKDIR /data

RUN echo 'cad3u2$che bust'

RUN git clone https://github.com/jeremylow/himawari_bot.git

RUN mkdir /data/himawari_bot/hires /data/himawari_bot/lowres /data/himawari_bot/videos

RUN /bin/bash /data/himawari_bot/bootstrap.sh

RUN cp /data/himawari_bot/himawari_cron /etc/cron.d/
