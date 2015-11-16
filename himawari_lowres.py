import os
from os.path import abspath, dirname, join

import datetime
import requests
import subprocess
import shlex

from PIL import Image

import tweepy
import himawari_config

BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'lowres.log')
LOWRES_FOLDER = join(BASE_DIR, 'lowres')

JMA_URL = "http://www.jma.go.jp/en/gms/imgs_c/6/visible/0/"

CONVERSION_COMMAND = (
    'convert {input_name}  -thumbnail {size}  -quality {qual}'
    ' -unsharp 0.05x0.05+12+0.001'
    ' -filter Triangle'
    ' -define filter:support=4'
    ' -define jpeg:fancy-upsampling=off'
    ' -define png:compression-filter=5'
    ' -define png:compression-level=9'
    ' -define png:compression-strategy=1'
    ' -define png:exclude-chunk=all'
    ' -interlace Line'
    ' -modulate 110,160,107'
    ' {output_name}')


def _get_api():
    auth = tweepy.OAuthHandler(
        himawari_config.CONSUMER_KEY,
        himawari_config.CONSUMER_SECRET)
    auth.set_access_token(himawari_config.ACCESS_KEY,
                          himawari_config.ACCESS_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    return api


def _round_time_30(dt):
    # Round date down to nearest 1/2 hour, then remove seconds & microseconds
    rounded_date = dt - datetime.timedelta(minutes=dt.minute % 30)
    rounded_date = rounded_date.replace(second=0, microsecond=0)

    # Give them time to upload new image
    rounded_date -= datetime.timedelta(minutes=30)
    return rounded_date


def _date_to_jma_filename(date):
    """
    Just for the JMA images. Converts a datetime object into a filename in the
    form of 201510311230-00.png

    Args:
        datetime: datetime object

    Returns:
        filename (str): I.e., 201510311230-00.png
    """
    fn = "{0}-{1}".format(
        date.strftime("%Y%m%d%H%M"),
        '00.png')
    return fn


def _get_jma_images(start_time=None):
    """
    Get the most recent 20 images from the JMA.

    Returns:
        images (list): List of 20 filenames for images to download.
    """
    images = []
    for i in range(0, 20):
        fn = _date_to_jma_filename(start_time - datetime.timedelta(minutes=30))
        images.append(fn)
        start_time -= datetime.timedelta(minutes=30)
    return images


def resize_and_crop_image_for_gif(image):
    im = Image.open(image)

    # Crop blue bar from bottom of image.
    im = im.crop((0, 0, 800, 800))
    im.save(image)

    cmd = CONVERSION_COMMAND.format(
        input_name=image,
        size=500,
        qual=90,
        output_name=image)
    subprocess.call(shlex.split(cmd))


def download_jma_images():
    """
    Downloads the most recent(ish) 20 images from the JMA.

    Returns:
        ISO date of last image.
    """
    now = datetime.datetime.utcnow()
    rounded_now = _round_time_30(now)
    images = _get_jma_images(start_time=rounded_now)

    for image in images:
        image_name = os.path.basename(image)
        with open('lowres/' + image_name, 'wb') as f:
            image_url = JMA_URL + image
            data = requests.get(image_url)
            f.write(data._content)
        resize_and_crop_image_for_gif('lowres/' + image_name)

    return rounded_now.isoformat()


def images_to_gif():
    cmd = ("bash mp4_to_gif.sh gif.gif")
    subprocess.call(shlex.split(cmd))

    return os.path.realpath("./gif.gif")


def tweet_gif(gif, status):
    api = _get_api()
    api.update_with_media(gif, status=status)


def main():
    status = download_jma_images()
    gif = images_to_gif()
    try:
        tweet_gif(gif, status)
    except Exception as e:
        print(e)
    subprocess.call('rm lowres/*.png', shell=True)
    subprocess.call('rm gif.gif', shell=True)


def make_local_gif():
    status = download_jma_images()
    gif = images_to_gif()
    print(status)
    print(gif)
    subprocess.call('rm lowres/*.png', shell=True)


if __name__ == '__main__':
    make_local_gif()
