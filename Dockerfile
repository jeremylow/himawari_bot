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

RUN apt-get install -y tree

WORKDIR /data

RUN echo 'cad32$che bust'

RUN git clone https://github.com/jeremylow/himawari_bot.git

RUN mkdir /data/himawari_bot/hires /data/himawari_bot/lowres /data/himawari_bot/videos

RUN /bin/bash /data/himawari_bot/bootstrap.sh
