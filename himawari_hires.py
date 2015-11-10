from __future__ import print_function

import os
from os.path import abspath, dirname, join

import datetime
import imghdr
import json
import logging
import logging.handlers
import random
import re
import requests
import subprocess

from PIL import Image

from bs4 import BeautifulSoup

import tweepy
from shapely.geometry import Point, MultiPoint

import config
import geometry

BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'hires.log')
HIRES_FOLDER = join(BASE_DIR, 'hires')


def now():
    return datetime.datetime.utcnow().isoformat()


def post_slack(msg):
    payload = {'text': msg}
    requests.post(
        config.SLACK_URL,
        json.dumps(payload),
        headers={'content-type': 'application/json'})


class HiResSequence(object):

    def __init__(self, *args, **kwargs):
        self.CIRA_IMG_BASE_URL = (
            "http://rammb.cira.colostate.edu/ramsdis/online/")

        self.CIRA_LIST_URL = (
            "http://rammb.cira.colostate.edu/ramsdis/online/archive_hi_res.asp"
            "?data_folder=himawari-8/full_disk_ahi_true_color"
            "&width=800&height=800")

        self.POINTS = [
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
        self.EARTH_POLYGON = MultiPoint(self.POINTS).convex_hull

        self.logger = logging.getLogger('HiResLogger')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(
            LOGFILE,
            maxBytes=1024*1024,
            backupCount=5)
        self.logger.addHandler(handler)
        self.logger.debug("{0}: Initialized HiResSequence".format(
            now()
        ))

    def _get_api(self):
        try:
            auth = tweepy.OAuthHandler(
                config.CONSUMER_KEY,
                config.CONSUMER_SECRET)
            auth.set_access_token(config.ACCESS_KEY,
                                  config.ACCESS_SECRET)
            api = tweepy.API(auth, wait_on_rate_limit=True)
            return api
        except Exception as e:
            print(e)
            self.logger.debug("{0}: {1}".format(
                now(), e))
            return False

    def _get_start_coord(self):
        """
        Get a top-left point to start our downward-rightward crop that
        is inside the Earth polygon

        Returns:
            coordinate tuple (0, 0 being top, left)
        """
        self.logger.debug("{0}: Getting coordinates".format(now()))
        while True:
            p = Point(random.randint(1, 4219), random.randint(732, 5499))
            if p.within(self.EARTH_POLYGON):
                break
            else:
                continue
        # When returning the Y Coordinate, need to reverse axis,
        # since Shapely counts up from bottom right and PIL counts
        # down from top left.
        lng_px, lat_px = (int(p.x), int(5500 - p.y))
        return (lat_px, lng_px)

    def _crop_hires_images(self, images, lat_start=None, lng_start=None):
        """
        Create a set of 720,720 png images cropped from the
        5500 x 5500 full-sized images.

        Args:
            images (list): List of hi-res images to crop down.
            lat_start, lng_start: upper, left-most point to start the crop

        Returns:
            list of cropped images
        """
        self.logger.debug("{0}: Cropping images".format(now()))
        width, height = 720, 720
        top, left = lat_start, lng_start

        for idx, image in enumerate(sorted(images)):
            filename = join(HIRES_FOLDER, image)
            print("got ", filename)

            # If imghdr can't ID the file, then it's probably corrupt and we'll
            # just drop that frame and delete the file.
            if not imghdr.what(filename):
                os.remove(filename)
                continue

            try:
                im = Image.open(filename)
                im2 = im.crop((left, top, left+width, top+height))
                crop_fn = "img{0}.png".format(str(idx).zfill(3))
                im2.save(join(BASE_DIR, crop_fn))
            except Exception as e:
                self.logger.debug("{0}: {1} failed with exception {2}".format(
                    now(),
                    str(filename),
                    str(e)))

    def _get_cira_images(self, num=60):
        """
        Scrapes the CIRA site for links to hi-res images.

        Returns:
            files (list): List of urls to download
        """
        self.logger.debug("{0}: Fetching images".format(now()))
        page_content = requests.get(self.CIRA_LIST_URL)._content
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all(
            'a',
            string=re.compile('^Hi-Res Image'),
            limit=num)

        image_urls = [link.attrs['href'] for link in links]

        prev_downloaded_images = os.listdir(HIRES_FOLDER)

        for image in image_urls:
            image_name = os.path.basename(image)
            full_image_url = "{0}{1}".format(
                    self.CIRA_IMG_BASE_URL,
                    image)

            if image_name in prev_downloaded_images:
                # Don't redownload images we already have.
                continue

            with open(join(HIRES_FOLDER, image_name), 'wb') as f:
                data = requests.get(full_image_url)
                f.write(data._content)

            if os.path.getsize(join(HIRES_FOLDER, image_name)) < 1024:
                os.remove(join(HIRES_FOLDER, image_name))
        return True

    @staticmethod
    def _delete_old_cira_images(num=60):
        """
        Only keep the most recent `num` images (my server is not *that* large)
        """
        images = sorted(os.listdir(HIRES_FOLDER))

        num_images_to_del = len(images) - num
        if num_images_to_del <= 0:
            return True
        for img in images[:abs(num_images_to_del)]:
            os.remove(join(HIRES_FOLDER, img))
        return True

    def refresh_images(self, num=60):
        self.logger.debug("{0}: Refreshing images".format(now()))
        self._get_cira_images(num=num)
        self._delete_old_cira_images(num=num)

    def make_hires_animation(self,
                             lat_start=None,
                             lng_start=None,
                             refresh=False):
        self.logger.debug("{0}: Making animation".format(now()))
        if refresh:
            self.refresh_images(num=90)

        images = os.listdir(HIRES_FOLDER)
        out = join(BASE_DIR, "{0}.mp4".format(
            datetime.datetime.utcnow().strftime("%Y%m%d%H%M")))

        if not (lat_start and lng_start):
            lat_start, lng_start = self._get_start_coord()

        self._crop_hires_images(images,
                                lat_start=lat_start,
                                lng_start=lng_start)
        coordinates = geometry.px_to_lat_long(lat_start+360, lng_start+360)

        cmd = "{0}/hires_mp4.sh {1} {2}".format(BASE_DIR, BASE_DIR, out)
        print(cmd)
        subprocess.call("{0}/hires_mp4.sh {1} {2}".format(
                BASE_DIR,
                BASE_DIR,
                out),
            shell=True)
        mp4_path = os.path.realpath(out)

        self.logger.debug("{0}: Coord: {1}, MP4: {2}".format(
            now(),
            coordinates,
            mp4_path))

        return (coordinates, mp4_path)

    def tweet_video(self, coordinates=None, mp4=None):
        msg = "{0}: Starting tweet".format(now())
        self.logger.debug(msg)
        post_slack(msg=msg)

        if not mp4:
            self.refresh_images(num=75)
            coordinates, mp4 = self.make_hires_animation()

        try:
            api = self._get_api()
            response = json.loads(
                api.video_upload(filename=mp4, max_size=15728640))
            api.update_status(
                status="Coordinates: {0}".format(str(coordinates)),
                media_ids=[response['media_id']])
        except Exception as e:
            self.logger.exception(e)
            post_slack(msg=e.__repr__())
        os.remove(mp4)
        msg = "{0}: Finished tweet".format(now())
        self.logger.debug(msg)
        post_slack(msg)


def make_local_video():
    seq = HiResSequence()
    coordinates, mp4 = seq.make_hires_animation(
        refresh=False)
    print(coordinates, mp4)


def tweet_video():
    seq = HiResSequence()
    seq.tweet_video()

if __name__ == '__main__':
    print(BASE_DIR)
    tweet_video()
