from __future__ import print_function

import os
import datetime
import json
import logging
import logging.handlers
import random
import re
import requests
import subprocess
import shlex

from PIL import Image

from bs4 import BeautifulSoup

import tweepy
from shapely.geometry import Point, MultiPoint

import config
import geometry

LOGFILE = 'hires.log'


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
            self.logger.debug("{0} : {1}".format(
                datetime.datetime.utcnow().isoformat(), e))
            return False

    def _get_start_coord(self):
        """
        Get a top-left point to start our downward-rightward crop that
        is inside the Earth polygon

        Returns:
            coordinate tuple (0, 0 being top, left)
        """
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

    @staticmethod
    def _crop_hires_images(images, lat_start=None, lng_start=None):
        """
        Create a set of 800x800 png images cropped from the
        5500 x 5500 full-sized images.

        Args:
            images (list): List of hi-res images to crop down.
            lat_start, lng_start: upper, left-most point to start the crop

        Returns:
            None
        """
        width, height = 720, 720
        top, left = lat_start, lng_start

        for idx, image in enumerate(sorted(images)):
            filename = 'hires/' + image
            print("got ", filename)
            im = Image.open(filename)
            im2 = im.crop((left, top, left+width, top+height))
            im2.save("img{0}.png".format(str(idx).zfill(3)))

    def _get_cira_images(self, num=60):
        """
        Scrapes the CIRA site for links to hi-res images.

        Returns:
            files (list): List of urls to download
        """
        page_content = requests.get(self.CIRA_LIST_URL)._content
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all(
            'a',
            string=re.compile('^Hi-Res Image'),
            limit=num)

        image_urls = [link.attrs['href'] for link in links]

        prev_downloaded_images = os.listdir('hires/')

        for image in image_urls:
            print(image)
            image_name = os.path.basename(image)
            full_image_url = "{0}{1}".format(
                    self.CIRA_IMG_BASE_URL,
                    image)
            print(full_image_url)

            if image_name in prev_downloaded_images:
                # Don't redownload images we already have.
                continue

            with open('hires/' + image_name, 'wb') as f:
                data = requests.get(full_image_url)
                f.write(data._content)
            if os.path.getsize('hires/' + image_name) < 1024:
                os.remove('hires/' + image_name)
        return True

    @staticmethod
    def _delete_old_cira_images(num=60):
        """
        Only keep the most recent `num` images (my server is not that large)
        """
        images = sorted(os.listdir('hires/'))

        num_images_to_del = len(images) - num
        if num_images_to_del <= 0:
            return True
        for img in images[:abs(num_images_to_del)]:
            os.remove('hires/' + img)
        return True

    def refresh_images(self, num=60):
        self._get_cira_images(num)
        self._delete_old_cira_images(num=num)

    def make_hires_animation(self,
                             lat_start=None,
                             lng_start=None,
                             refresh=False):
        if refresh:
            self.refresh_images(num=90)
        images = os.listdir('hires/')
        out = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")

        if not (lat_start and lng_start):
            lat_start, lng_start = self._get_start_coord()

        self._crop_hires_images(images,
                                lat_start=lat_start,
                                lng_start=lng_start)
        coordinates = geometry.px_to_lat_long(lat_start+400, lng_start+400)

        cmd = ("ffmpeg -framerate 6 -i img%03d.png "
               "-c:v libx264 -vf fps=6 -pix_fmt yuv420p {0}.mp4".format(out))
        subprocess.call(shlex.split(cmd))
        mp4_path = os.path.realpath("./{0}.mp4".format(out))

        self.logger.debug("{0}: Coord: {1}, MP4: {2}".format(
            datetime.datetime.utcnow().isoformat(),
            coordinates,
            mp4_path))

        subprocess.call('rm *.png', shell=True)
        return (coordinates, mp4_path)

    def tweet_video(self, coordinates=None, mp4=None):
        if not mp4:
            self.refresh_images(num=90)
            coordinates, mp4 = self.make_hires_animation()

        try:
            api = self._get_api()
            response = json.loads(
                api.video_upload(filename=mp4, max_size=15728640))
            api.update_status(
                status="Coordinates: {0}".format(str(coordinates)),
                media_ids=[response['media_id']])
        except Exception as e:
            self.logger.debug("{0}: {1}".format(
                datetime.datetime.utcnow().isoformat(), e))
        os.remove(mp4)


def make_local_video():
    seq = HiResSequence()
    coordinates, mp4 = seq.make_hires_animation(
        refresh=False)
    print(coordinates, mp4)


def tweet_video():
    seq = HiResSequence()
    seq.tweet_video()

if __name__ == '__main__':
    # make_local_video()
    tweet_video()
