import os
import datetime
import random
import re
import requests
import subprocess
import shlex

from PIL import Image

from bs4 import BeautifulSoup

import tweepy
from shapely.geometry import Point, MultiPoint

import himawari_config
import geometry


class HiResSequence(object):

    def __init__(self, *args, **kwargs):
        self.CIRA_IMG_BASE_URL = (
            "http://rammb.cira.colostate.edu/ramsdis/online/images/hi_res/"
            "himawari-8/full_disk_ahi_true_color/")

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

    @staticmethod
    def _get_api():
        auth = tweepy.OAuthHandler(
            himawari_config.CONSUMER_KEY,
            himawari_config.CONSUMER_SECRET)
        auth.set_access_token(himawari_config.ACCESS_KEY,
                              himawari_config.ACCESS_SECRET)
        api = tweepy.API(auth, wait_on_rate_limit=True)
        return api

    @staticmethod
    def _px_to_lat_lng(start_pts):
        x, y = start_pts
        x += 2750
        y += 2750
        lat_km, lng_km = geometry.px_to_km(x, y)
        lat, lng = geometry.km_to_lat_lng(lat_km, lng_km)

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
    def _crop_hires_images(images, start_pts):
        """
        Create a set of 1280x720 png images cropped from the
        5500 x 5500 full-sized images.

        Args:
            images (list): List of hi-res images to crop down.
            start_pts (tuple): Tuple of integers at which to start the crop.
                Should be in the form of (leftMostPoint, topMostPoint).

        Returns:
            None
        """
        width, height = 1280, 720
        left, top = start_pts

        for idx, image in enumerate(sorted(images)):
            filename = 'hires/' + image
            print(filename)
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
            image_name = os.path.basename(image)

            if image_name in prev_downloaded_images:
                # Don't redownload images we already have.
                continue

            with open('hires/' + image_name, 'wb') as f:
                data = requests.get("{0}{1}".format(
                    self.CIRA_IMG_BASE_URL,
                    image))
                f.write(data._content)
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

    def make_hires_animation(self):
        images = os.listdir('hires/')
        out = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
        start_pts = self._get_start_coord()
        self._crop_hires_images(images, start_pts)
        coordinates = self._px_to_lat_lng(start_pts)
        cmd = ("ffmpeg -framerate 8 -i img%03d.png "
               "-c:v libx264 -vf fps=8 -pix_fmt yuv420p {0}.mp4".format(out))
        subprocess.call(shlex.split(cmd))
        mp4_path = os.path.realpath("./{0}.mp4".format(out))
        return (coordinates, mp4_path)


def main():
    seq = HiResSequence()
    mp4 = seq.make_hires_animation()
    print(mp4)

if __name__ == '__main__':
    main()
