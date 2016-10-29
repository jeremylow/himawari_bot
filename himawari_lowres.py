import os
from os.path import abspath, dirname, join

import datetime
import logging
import logging.handlers
import requests
import subprocess
import shlex

from PIL import Image

import twitter
import config

BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'lowres.log')
LOWRES_FOLDER = join(BASE_DIR, 'lowres/')
JMA_URL = "http://himawari8-dl.nict.go.jp/himawari8/img/D531106/1d/550/"

LOG_FILENAME = os.path.join(BASE_DIR, 'lowres.log')


def set_up_logging(level=logging.DEBUG):
    global logger
    logger = logging.getLogger('LowResLogger')
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1048576, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_api():
    api = twitter.Api(
        config.CONSUMER_KEY,
        config.CONSUMER_SECRET,
        config.ACCESS_KEY,
        config.ACCESS_SECRET,
        sleep_on_rate_limit=True)
    logger.debug('using Api: {0}'.format(api))
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
    Get the most recent [num] images from the JMA.

    Returns:
        images (list): List of [num] filenames for images to download.
    """
    logger.debug('getting images')
    if not start_time:
        start_time = round_time_10(datetime.datetime.utcnow())
    images = []
    for i in range(0, num):
        fn = date_to_jma_filename(round_time_10(start_time))
        images.append(fn)
        start_time -= datetime.timedelta(minutes=10)
    logger.debug('using image list: {0}'.format(images))
    return images


def delete_old_images(num=48):
    """
    Only keep the most recent `num` images (my server is not *that* large)
    """
    images = sorted(os.listdir(LOWRES_FOLDER))

    num_images_to_del = len(images) - num
    if num_images_to_del <= 0:
        return True
    images_to_del = images[:abs(num_images_to_del)]
    for img in images_to_del:
        if os.path.splitext(img)[1] != '.png':
            continue
        logger.debug('deleting {0}'.format(img))
        os.remove(join(LOWRES_FOLDER, img))
    return True


def process_image(image):
    logger.debug('processing image: {0}'.format(image))
    im = Image.open(image)
    old_size = im.size
    new_size = (650, 650)
    new_im = Image.new("RGB", new_size)
    new_im.paste(im, ((new_size[0]-old_size[0])//2,
                      (new_size[1]-old_size[1])//2))
    new_im = new_im.resize((500,500))
    new_im.save(image)


def download_jma_images():
    """
    Downloads the most recent(ish) 20 images from the JMA.

    Returns:
        ISO date of last image.
    """
    logger.debug('downloading images')
    rounded_now = round_time_10(datetime.datetime.utcnow())
    logger.debug('rounded time is {0}'.format(rounded_now))
    images = get_jma_images(start_time=rounded_now)
    logger.debug('images: {0}'.format(str(images)))

    old_images = os.listdir(LOWRES_FOLDER)
    logger.debug('old_images: {0}'.format(old_images))

    for image in images:
        image_name = image.replace('/', '')
        if image_name in old_images:
            logger.debug('skipping {0}'.format(image_name))
            continue
        logger.debug('downloading {0}'.format(image_name))
        image_url = JMA_URL + image
        data = requests.get(image_url)
        if len(data._content) < 2**13:
            continue
        with open(LOWRES_FOLDER + image_name, 'wb') as f:
            f.write(data._content)
        process_image(LOWRES_FOLDER + image_name)
    return rounded_now.isoformat()


def images_to_gif():
    logger.debug('creating GIF')
    cmd = ("bash {0}/mp4_to_gif.sh {0} {0}/gif.gif".format(BASE_DIR))
    subprocess.call(shlex.split(cmd))
    return os.path.realpath("{0}/gif.gif".format(BASE_DIR))


def tweet_gif(gif, status):
    api = get_api()
    uploaded_gif = api.UploadMediaChunked(media=gif, media_category="tweet_gif")
    logger.debug('media ID: {0}'.format(uploaded_gif))
    status = api.PostUpdate(status=status, media=uploaded_gif)
    logger.debug('status: {0}'.format(status))
    return status


def main():
    status = download_jma_images()
    delete_old_images()
    gif = images_to_gif()
    try:
        tweet_gif(gif, status)
    except Exception as e:
        logger.critical(str(e))


def make_local_gif():
    status = download_jma_images()
    gif = images_to_gif()
    print(status)
    print(gif)


if __name__ == '__main__':
    set_up_logging()
    logger.debug('started program')
    main()
