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

from celery_conf import app

import himawari_config
import geometry

JMA_URL = "http://www.jma.go.jp/en/gms/imgs_c/6/visible/0/"

CIRA_IMG_BASE_URL = (
    "http://rammb.cira.colostate.edu/ramsdis/online/images/hi_res/"
    "himawari-8/full_disk_ahi_true_color/")

CIRA_LIST_URL = (
    "http://rammb.cira.colostate.edu/ramsdis/online/"
    "archive_hi_res.asp?data_folder=himawari-8/full_disk_ahi_true_color"
    "&width=800&height=800")


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


def _get_start_coord():
    """
    Get a top-left point to start our downward-rightward crop that
    is inside the Earth polygon

    Returns:
        coordinate tuple (0,0 being top-left)
    """
    while True:
        p = Point(random.randint(1, 4219), random.randint(732, 5499))
        if p.within(EARTH_POLYGON):
            break
        else:
            continue
    # When returning the Y Coordinate, need to reverse axis,
    # since Shapely counts up from bottom right and PIL counts
    # down from top left.
    lat_px, lng_px = (int(p.x), int(5500 - p.y))
    return (lat_px, lng_px)


def crop_hires_images(images):
    """
    Create a set of 1280x720 png images cropped from the
    5500 x 5500 full-sized images.

    Args:
        images (list): List of hi-res images to crop down.

    Returns:
        None
    """
    width, height = 1280, 720
    left, top = _get_start_coord()

    for idx, image in enumerate(sorted(images)):
        filename = 'hires/' + image
        print(filename)
        im = Image.open(filename)
        im2 = im.crop((left, top, left+width, top+height))
        im2.save("img{0}.png".format(str(idx).zfill(3)))


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


def _get_cira_images():
    """
    Scrapes the CIRA site for links to hi-res images.

    Returns:
        files (list): List of urls to download
    """
    page_content = requests.get(CIRA_LIST_URL)._content
    soup = BeautifulSoup(page_content, 'html.parser')
    links = soup.find_all('a', string=re.compile('^Hi-Res Image'), limit=48)

    image_urls = [link.attrs['href'] for link in links]

    prev_downloaded_images = os.listdir('hires/')

    for image in image_urls:
        image_name = os.path.basename(image)

        if image_name in prev_downloaded_images:
            # Don't redownload images we already have.
            continue

        with open('hires/' + image_name, 'wb') as f:
            data = requests.get("{0}{1}".format(
                CIRA_IMG_BASE_URL,
                image))
            f.write(data._content)
    return True


def _delete_old_cira_images():
    """
    Only keep the most recent 48 images (my server is not that large)
    """
    images = sorted(os.listdir('hires/'))
    num_images_to_del = len(images) - 48
    if num_images_to_del <= 0:
        return True
    for img in images[:abs(num_images_to_del)]:
        os.remove('hires/' + img)
    return True


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


def make_hires_animation():
    images = os.listdir('hires/')
    output_name = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
    crop_hires_images(images)
    cmd = ("ffmpeg -framerate 8 "
           "-i img%03d.png "
           "-c:v libx264 -vf fps=8 -pix_fmt yuv420p {0}.mp4".format(output_name))
    subprocess.call(shlex.split(cmd))
    mp4_path = os.path.realpath("./out.mp4")
    return mp4_path


def tweet_gif(gif, status):
    api = _get_api()
    api.update_with_media(gif, status=status)


@app.task
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
