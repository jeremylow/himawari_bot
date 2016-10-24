import os
from os.path import abspath, dirname, join

import datetime
import requests
import subprocess
import shlex

from PIL import Image

import twitter
import config

BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'lowres.log')
LOWRES_FOLDER = join(BASE_DIR, 'lowres')

JMA_URL = "http://himawari8-dl.nict.go.jp/himawari8/img/D531106/1d/550/"


def get_api():
    api = twitter.Api(
        config.CONSUMER_KEY,
        config.CONSUMER_SECRET,
        config.ACCESS_KEY,
        config.ACCESS_SECRET,
        sleep_on_rate_limit=True)
    return api


def round_time_10(dt):
    # Round date down to nearest 0.1 hour, then remove seconds & microseconds
    rounded_date = dt - datetime.timedelta(minutes=dt.minute % 10)
    rounded_date = rounded_date.replace(second=0, microsecond=0)

    # Give them time to upload new image
    rounded_date -= datetime.timedelta(minutes=10)
    return rounded_date


def date_to_jma_filename(date):
    """
    Just for the JMA images. Converts a datetime object into a filename in the
    form of:
    "http://himawari8-dl.nict.go.jp/himawari8/img/D531106/1d/550/2016/10/23/115000_0_0.png"

    Args:
        datetime: datetime object

    Returns:
        filename (str): I.e., 201510311230-00.png
    """
    return date.strftime("%Y/%m/%d/%H%M00_0_0.png")


def get_jma_images(start_time=None, num=48):
    """
    Get the most recent 20 images from the JMA.

    Returns:
        images (list): List of 20 filenames for images to download.
    """
    if not start_time:
        start_time = round_time_10(datetime.datetime.utcnow())
    images = []
    for i in range(0, num):
        fn = date_to_jma_filename(round_time_10(start_time))
        images.append(fn)
        start_time -= datetime.timedelta(minutes=10)
    return images


def process_image(image):
    im = Image.open(image)
    old_size = im.size
    new_size = (650, 650)
    new_im = Image.new("RGB", new_size)
    new_im.paste(im, ((new_size[0]-old_size[0])//2,
                      (new_size[1]-old_size[1])//2))
    new_im.save(image)


def download_jma_images():
    """
    Downloads the most recent(ish) 20 images from the JMA.

    Returns:
        ISO date of last image.
    """
    rounded_now = round_time_10(datetime.datetime.utcnow())
    images = get_jma_images(start_time=rounded_now)

    old_images = os.listdir('lowres')

    for image in images:
        image_name = os.path.basename(image)
        image_name = image.replace('/', '')
        if image_name in old_images:
            continue
        image_url = JMA_URL + image
        data = requests.get(image_url)
        if len(data._content) < 2**13:
            continue
        with open('lowres/' + image_name, 'wb') as f:
            f.write(data._content)
        process_image('lowres/' + image_name)
    return rounded_now.isoformat()


def images_to_gif():
    cmd = ("bash mp4_to_gif.sh gif.gif")
    subprocess.call(shlex.split(cmd))
    return os.path.realpath("./gif.gif")


def tweet_gif(gif, status):
    api = get_api()
    uploaded_gif = api.UploadMediaChunked(media=gif, media_category="tweet_gif")
    api.PostUpdate(status=status, media=uploaded_gif)


def main():
    status = download_jma_images()
    gif = images_to_gif()
    try:
        tweet_gif(gif, status)
    except Exception as e:
        print(e)


def make_local_gif():
    status = download_jma_images()
    gif = images_to_gif()
    print(status)
    print(gif)


if __name__ == '__main__':
    make_local_gif()
