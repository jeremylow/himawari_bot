FROM armv7/armhf-ubuntu:14.04
MAINTAINER Jeremy Low <jeremy@hrhs.co.uk>

ENV TERM linux

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y build-essential && \
    apt-get install -y software-properties-common

RUN add-apt-repository -y ppa:mc3man/trusty-media
RUN apt-get update && apt-get install -y \
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

RUN git pull https://github.com/jeremylow/himawari_bot.git
RUN bootstrap.sh

WORKDIR /data

CMD cron
