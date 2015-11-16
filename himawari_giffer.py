# File is not used. Just various testing things.


import os
import datetime
import random
import requests
import subprocess
import shlex

from PIL import Image

from shapely.geometry import Point, MultiPoint

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
            # When returning the Y Coordinate, need to reverse axis,
            # since Shapely counts up from bottom right and PIL counts
            # down from top left.
            return (int(p.x), int(5500 - p.y))
            break
        else:
            continue


def crop_hires_images(images):
    """
    Create a set of hi-res, 1280x720 png images cropped from the
    5500 x 5500 full-sized images.

    Args:
        images (list): List of hi-res images to crop down.

    Returns:
        None
    """
    width, height = 1280, 720
    left, top = _get_start_coord()

    for idx, image in enumerate(sorted(images)):
        filename = 'images/' + image
        print(filename)
        im = Image.open(filename)
        im2 = im.crop((left, top, left+width, top+height))
        im2.save("img{0}.png".format(str(idx).zfill(3)))


def _round_time(dt):
    # Round date down to nearest 1/2 hour, then remove seconds & microseconds
    rounded_date = dt - datetime.timedelta(minutes=dt.minute % 30)
    rounded_date = rounded_date.replace(second=0, microsecond=0)

    # Give the JMA time to upload new image
    rounded_date -= datetime.timedelta(minutes=30)
    return rounded_date


def _date_to_filename(datetime):
    """
    Just for the JMA images. Converts a datetime object into a filename in the
    form of 201510311230-00.png

    Args:
        datetime: datetime object

    Returns:
        filename (str): I.e., 201510311230-00.png
    """
    fn = "{0}-{1}".format(datetime.strftime("%Y%m%d%H%M"), '00.png')
    return fn


def _get_recent_images_list(start_time=None):
    images = []
    for i in range(0, 36):
        fn = _date_to_filename(start_time - datetime.timedelta(minutes=30))
        images.append(fn)
        start_time -= datetime.timedelta(minutes=30)
    return images


def resize_image(image):
    im = Image.open(image)

    # Crop blue bar from bottom of image.
    im = im.crop((0, 0, 800, 800))
    im.save(image)

    cmd = CONVERSION_COMMAND.format(
        input_name=image,
        size=800,
        qual=100,
        output_name=image)
    subprocess.call(shlex.split(cmd))


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


def hires_animation():
    images = os.listdir('images/')
    crop_hires_images(images)
    cmd = ("ffmpeg -framerate 5 "
           "-i img%03d.png "
           "-c:v libx264 -vf fps=5 -pix_fmt yuv420p out.mp4")
    subprocess.call(shlex.split(cmd))
    mp4_path = os.path.realpath("./out.mp4")
    return mp4_path


if __name__ == '__main__':
    hires_animation()
