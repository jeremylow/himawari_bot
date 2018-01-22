import datetime
from ftplib import FTP
import os
from os.path import abspath, dirname, join
import shlex
import subprocess
import time

from common import get_api, set_up_logging


BASE_DIR = dirname(abspath(__file__))
LOGFILE = join(BASE_DIR, 'lowres.log')
LOWRES_FOLDER = join(BASE_DIR, 'lowres/')


def round_time_10(dt):
    # Round date down to nearest 0.1 hour, then remove seconds & microseconds
    logger.debug("Rounding {0}".format(dt))
    rounded_date = dt - datetime.timedelta(minutes=dt.minute % 10)
    rounded_date = rounded_date.replace(second=0, microsecond=0)

    # Give them time to upload new image
    rounded_date -= datetime.timedelta(minutes=10)
    logger.debug("Rounded to {0}".format(rounded_date))
    return rounded_date


def download_images(num=48):
    """
    Downloads the most recent `num` images.

    Returns:
        ISO date of last image.
    """
    with FTP("ftp.nnvl.noaa.gov") as ftp:
        ftp.login()
        ftp.cwd('GOES/HIMAWARI/simplecontrast')
        images = list(reversed(sorted(list(ftp.nlst()))))  # ridiculous

        logger.debug('downloading images')
        rounded_now = round_time_10(datetime.datetime.utcnow())
        logger.debug('rounded time is {0}'.format(rounded_now))
        logger.debug('images: {0}'.format(str(images)))

        old_images = os.listdir(LOWRES_FOLDER)
        logger.debug('old_images: {0}'.format(old_images))

        # import pdb; pdb.set_trace()
        for image in images[:num]:
            if image in old_images:
                logger.debug('skipping {0}'.format(image))
                continue
            elif os.path.splitext(image)[1] != '.JPG':
                continue
            logger.debug('downloading {0}'.format(image))
            ftp.retrbinary('RETR {0}'.format(image), open(join(LOWRES_FOLDER, image.replace(':', '')), 'wb').write)
        return rounded_now.isoformat()


def delete_old_images(num=48):
    """
    Only keep the most recent `num` images (my server is not *that* large)
    """
    logger.debug("Starting delete of old images")
    images = sorted(os.listdir(LOWRES_FOLDER))

    num_images_to_del = len(images) - num
    if num_images_to_del <= 0:
        return True
    images_to_del = images[:abs(num_images_to_del)]
    for image in images_to_del:
        if os.path.splitext(image)[1] != '.JPG':
            continue
        logger.debug('deleting {0}'.format(image))
        os.remove(join(LOWRES_FOLDER, image))
    return True


def images_to_gif():
    logger.debug('creating GIF')
    cmd = ("{0}/giffer_2.sh {1} {0}/gif.mp4".format(BASE_DIR, LOWRES_FOLDER))
    logger.debug(cmd)
    subprocess.call(shlex.split(cmd))
    return os.path.realpath("{0}/gif.mp4".format(BASE_DIR))


def tweet_gif(gif, status):
    logger.debug("Starting to tweet")
    api = get_api()
    uploaded_gif = api.UploadMediaChunked(media=gif)
    logger.debug('media ID: {0}'.format(uploaded_gif))
    status = api.PostUpdate(status=status, media=uploaded_gif)
    logger.debug('Finished tweet: {0}'.format(status))
    return status


def main():
    date_time = download_images(num=220)
    delete_old_images(num=220)
    gif = images_to_gif()
    tweet_gif(gif, date_time)
    os.remove(gif)


if __name__ == '__main__':
    import logging
    logger = set_up_logging(log_file=LOGFILE, level=logging.DEBUG)
    logger.info('Started program')
    while True:
        try:
            main()
        except:
            pass
        time.sleep(10800)
