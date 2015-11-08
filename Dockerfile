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
RUN ls
RUN git clone https://github.com/jeremylow/himawari_bot.git
RUN tree /data

RUN echo '2cache bust'
RUN mkdir /data/himawari_bot/hires /data/himawari_bot/lowres /data/himawari_bot/videos

RUN ln -s /data/himawari_bot/himawari_cron /etc/cron.d/himawari_cron
RUN chmod 0644 /etc/cron.d/himawari_cron


CMD cron
