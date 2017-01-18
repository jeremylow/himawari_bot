#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 Jeremy Low
# License: MIT

"""Create high resolution MP4 from large full disk Himawari8 satellite images"""

from __future__ import print_function, unicode_literals, absolute_import

import os
from os.path import abspath, dirname, join, getsize

import imghdr
import logging
import logging.handlers
import random
import re
import requests
import subprocess

from PIL import Image

from bs4 import BeautifulSoup

import twitter
from shapely.geometry import Point, MultiPoint
from osm_shortlink import short_osm

import config
import geometry

BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'hires.log')
HIRES_FOLDER = join(BASE_DIR, 'hires')


CIRA_IMG_BASE_URL = ("http://rammb.cira.colostate.edu/ramsdis/online/")

CIRA_LIST_URL = (
    "http://rammb.cira.colostate.edu/ramsdis/online/archive_hi_res.asp"
    "?data_folder=himawari-8/full_disk_ahi_true_color"
    "&width=800&height=800")

POINTS = [
    # Clockwise from leftmost/higher middle ... one ?
    # Point being, we don't want to start somewhere way out in space,
    # because that is not interesting for this application.
    (0, 4275),
    (1225, 5500),
    (3500, 5500),
    (4220, 4970),
    (4220, 2025),
    (3000, 732),
    (1140, 732),
    (0, 1500)
]

# Polygon delimiting the 'interesting' parts of the Earth.
EARTH_POLYGON = MultiPoint(POINTS).convex_hull


def set_up_logging(level=logging.DEBUG):
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    handler = logging.handlers.RotatingFileHandler(LOGFILE,
                                                   maxBytes=1048576,
                                                   backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_api():
    """Returns an authenticated Twitter API instance"""
    logger.info('Getting API')
    api = twitter.Api(
        config.CONSUMER_KEY,
        config.CONSUMER_SECRET,
        config.ACCESS_KEY,
        config.ACCESS_SECRET,
        tweet_mode="extended",
        sleep_on_rate_limit=True)
    logger.debug('Using Api: %s', api)
    return api


def get_start_coord():
    """
    Get a top-left point to start our downward-rightward crop that
    is inside the Earth polygon

    Returns:
        coordinate tuple (0, 0 being top, left)
    """
    logger.info("Getting coordinates")
    while True:
        try_point = Point(random.randint(1, 4219), random.randint(732, 5499))
        if try_point.within(EARTH_POLYGON):
            break
        else:
            continue
    # When returning the Y Coordinate, need to reverse axis,
    # since Shapely counts up from bottom right and PIL counts
    # down from top left.
    lng_px, lat_px = (int(try_point.x), int(5500 - try_point.y))
    logger.debug("Using coordinates: (%s, %s)", lat_px, lng_px)
    return (lat_px, lng_px)


def crop_hires_images(images, lat_start=None, lng_start=None):
    """
    Create a set of 720,720 png images cropped from the
    5500 x 5500 full-sized images.

    Args:
        images (list): List of hi-res images to crop down.
        lat_start, lng_start: upper, left-most point to start the crop

    Returns:
        list of cropped images
    """
    logger.info("Cropping images")
    width, height = 720, 720
    top, left = lat_start, lng_start

    for idx, image in enumerate(sorted(images)):
        filename = join(HIRES_FOLDER, image)
        logger.debug("Cropping %s", filename)

        # If imghdr can't ID the file, then it's probably corrupt and we'll
        # just drop that frame and delete the file.
        if not imghdr.what(filename):
            logger.debug("Deleting %s", filename)
            os.remove(filename)
            continue

        try:
            im = Image.open(filename)
            im2 = im.crop((left, top, left+width, top+height))
            crop_fn = "img{0}.png".format(str(idx).zfill(3))
            im2.save(join(BASE_DIR, crop_fn))
        except Exception as e:
            logger.error("Failed to crop image.", exc_info=True)
            continue


def get_cira_images(num=60):
    """
    Scrapes the CIRA site for links to hi-res images.

    Returns:
        files (list): List of urls to download
    """
    logger.info("Fetching images")
    page_content = requests.get(CIRA_LIST_URL)._content
    soup = BeautifulSoup(page_content, 'html.parser')
    links = soup.find_all('a', string=re.compile('^Hi-Res Image'), limit=num)

    image_urls = [link.attrs['href'] for link in links]
    prev_downloaded_images = os.listdir(HIRES_FOLDER)

    for idx, image in enumerate(image_urls):
        logger.debug("Getting (%s / %s) image: %s", idx + 1, num, image)
        image_name = os.path.basename(image)
        full_image_url = "{0}{1}".format(CIRA_IMG_BASE_URL, image)
        download_name = join(HIRES_FOLDER, image_name)

        if image_name in prev_downloaded_images and getsize(download_name) > 1024:
            # Don't redownload images we already have.
            logger.debug("Skipping previously downloaded image %s", image_name)
            continue

        with open(download_name, 'wb') as f:
            data = requests.get(full_image_url)
            f.write(data._content)
            logger.debug("Successfully downloaded %s", full_image_url)

        # If the image is smaller than 1024 bytes, it's one of the broken ones
        if getsize(download_name) < 1024:
            logger.debug("Deleting corrupt image %s", image_name)
            os.remove(download_name)


def delete_old_cira_images(num=60):
    """Deletes all but the most recent `num` images.
    Args:
        num (int, optional): number of images to retain on the server
    """
    logger.info("Deleting old CIRA images")
    images = sorted(os.listdir(HIRES_FOLDER))

    num_images_to_del = len(images) - num
    logger.debug("Deleting %s images", num_images_to_del)

    if num_images_to_del <= 0:
        return True

    for img in images[:abs(num_images_to_del)]:
        logger.debug("Deleting %s", img)
        os.remove(join(HIRES_FOLDER, img))


def refresh_images(num=60):
    """Upadtes images for use by deleting old, getting new.
    Args:
        num (int, optional): number of images to end up with.
    """
    logger.info("Refreshing images")
    get_cira_images(num=num)
    delete_old_cira_images(num=num)


def make_hires_animation(lat_start=None, lng_start=None):
    """Creates a video with its center at the lat_start, lng_start pair
    Args:
        lat_start (float, int): center latitude point of the video
        lng_start (float, int): center longitude point of the video
    Returns:
        (tuple): Coordinates, path for MP4
    """
    logger.info("Making hi-res video")

    images = os.listdir(HIRES_FOLDER)
    out = join(BASE_DIR, "video_out.mp4")

    if not (lat_start and lng_start):
        lat_start, lng_start = get_start_coord()

    crop_hires_images(images, lat_start=lat_start, lng_start=lng_start)
    coordinates = geometry.px_to_lat_long(lat_start+360, lng_start+360)

    cmd = "{0}/hires_mp4.sh {1} {2}".format(BASE_DIR, BASE_DIR, out)
    logger.debug("Hires command: %s", cmd)
    subprocess.call("{0}/hires_mp4.sh {1} {2}".format(BASE_DIR, BASE_DIR, out), shell=True)
    mp4_path = os.path.realpath(out)
    return (coordinates, mp4_path)


def tweet_video(coordinates=None, mp4=None):
    logger.info("Starting tweet")

    if not mp4:
        refresh_images(num=55)
        coordinates, mp4 = make_hires_animation()

    short_link = short_osm(coordinates[0], coordinates[1], zoom=6, marker=True)
    logger.info(short_link)

    try:
        api = get_api()
        api.PostUpdate(
            status="Coordinates: {0}; {1}".format(str(coordinates), short_link),
            media=mp4)
    except Exception as e:
        logger.error("Failed to tweet", exc_info=True)
    os.remove(mp4)
    logger.info("Finished tweet")


if __name__ == '__main__':
    set_up_logging()
    tweet_video()
