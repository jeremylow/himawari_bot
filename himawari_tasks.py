import os
import datetime
import requests

import subprocess
import shlex

import tweepy

import himawari_config
from celery_conf import app

URL = "http://www.jma.go.jp/en/gms/imgs_c/6/visible/0/"

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
    ' -modulate 115,180,107'
    # ' -crop 800x800 +repage'
    ' {output_name}')


def _get_api():
    auth = tweepy.OAuthHandler(
        himawari_config.CONSUMER_KEY,
        himawari_config.CONSUMER_SECRET)
    auth.set_access_token(himawari_config.ACCESS_KEY,
                          himawari_config.ACCESS_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    return api


def _round_time(dt):
    # Round date down to nearest 1/2 hour, then remove seconds & microseconds
    rounded_date = dt - datetime.timedelta(minutes=dt.minute % 30)
    rounded_date = rounded_date.replace(second=0, microsecond=0)

    # Give them time to upload new image
    rounded_date -= datetime.timedelta(minutes=30)
    return rounded_date


def _date_to_filename(date):
    fn = "{0}-{1}".format(
        date.strftime("%Y%m%d%H%M"),
        '00.png')
    return fn


def _get_recent_images_list(start_time=None):
    images = []
    for i in range(0, 20):
        fn = _date_to_filename(start_time - datetime.timedelta(minutes=30))
        images.append(fn)
        start_time -= datetime.timedelta(minutes=30)
    return images


def resize_image(image):
    cmd = CONVERSION_COMMAND.format(
        input_name=image,
        size=450,
        qual=80,
        output_name=image)
    subprocess.call(shlex.split(cmd))

    # base, ext = os.path.splitext(image)

    # # Delete the cropped portion which is inexplicably saved during the
    # # cropping procedure in imagemagick.
    # subprocess.call(
    #     "rm {baseimage}-1{ext}".format(baseimage=base, ext=ext),
    #     shell=True)

    # # Delete the original image, leaving only the cropped image.
    # subprocess.call(
    #     "rm {image}".format(image=image),
    #     shell=True)


def scrape_image_links():
    now = datetime.datetime.utcnow()
    rounded_now = _round_time(now)
    images = _get_recent_images_list(start_time=rounded_now)

    for image in images:
        image_name = os.path.basename(image)
        with open(image_name, 'wb') as f:
            image_url = URL + image
            data = requests.get(image_url)
            f.write(data._content)
        resize_image(image_name)

    return rounded_now.isoformat()


def images_to_gif():
    cmd = "convert -delay 16 -loop 0 *.png gif.gif"
    subprocess.call(shlex.split(cmd))
    gif_path = os.path.realpath("./gif.gif")
    return gif_path


def tweet_gif(gif, status):
    api = _get_api()
    api.update_with_media(gif, status=status)


@app.task
def main():
    status = scrape_image_links()
    gif = images_to_gif()
    try:
        tweet_gif(gif, status)
    except Exception as e:
        print(e)
    subprocess.call('rm *.png', shell=True)
    subprocess.call('rm gif.gif', shell=True)

if __name__ == '__main__':
    main()
