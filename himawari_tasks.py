import os
import datetime
import requests
import re

import subprocess
import shlex

from bs4 import BeautifulSoup
import tweepy

import himawari_config

URL = (
    "http://rammb.cira.colostate.edu/ramsdis/online/"
    "archive_hi_res.asp?data_folder=himawari-8/full_disk_ahi_true_color"
    "&width=800&height=800")
LINK_BASE_URL = "http://rammb.cira.colostate.edu/ramsdis/online/"
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
    ' -modulate 115,110,100'
    ' {output_name}')


def _get_api():
    auth = tweepy.OAuthHandler(
        himawari_config.CONSUMER_KEY,
        himawari_config.CONSUMER_SECRET)
    auth.set_access_token(himawari_config.ACCESS_KEY,
                          himawari_config.ACCESS_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    return api


def resize_image(image):
    cmd = CONVERSION_COMMAND.format(
        input_name=image,
        size=500,
        qual=90,
        output_name=image)
    subprocess.call(shlex.split(cmd))


def scrape_image_links():
    page_content = requests.get(URL)._content
    soup = BeautifulSoup(page_content, 'html.parser')
    links = soup.find_all('a', string=re.compile('^Image'), limit=24)

    image_urls = [link.attrs['href'] for link in links]

    for image in image_urls:
        image_name = os.path.basename(image)
        with open(image_name, 'wb') as f:
            data = requests.get("{0}{1}".format(
                LINK_BASE_URL,
                image))
            f.write(data._content)
        resize_image(image_name)
    match = match = re.search(r'(?P<date>[\d]+)\.jpg', image_urls[0])
    last_image_datetime = datetime.datetime.strptime(
        match.group(1)[:12],
        "%Y%m%d%H%M")
    return last_image_datetime.isoformat()


def images_to_gif():
    cmd = "convert -delay 10 -loop 0 full_disk*.jpg gif.gif"
    subprocess.call(shlex.split(cmd))
    gif_path = os.path.realpath("./gif.gif")
    return gif_path


def tweet_gif(gif, status):
    api = _get_api()
    api.update_with_media(gif, status=status)


def main():
    status = scrape_image_links()
    gif = images_to_gif()
    tweet_gif(gif, status)
    subprocess.call(shlex.split('rm *.jpg'))
    subprocess.call(shlex.split('rm *.gif'))

if __name__ == '__main__':
    main()
