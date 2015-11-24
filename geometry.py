import pyproj


sat = pyproj.Proj('+proj=geos +lon_0=140.7 +h=35786369.500000000')


def lat_long_to_px(lat=None, lng=None):
    """
    Converts a latitude and longitude to the pixel value from the 5500x5500
    Himawari image. It's decidedly not perfect.

    Args:
        latitude (float): latitude coordinate
        longitude (float): longitude coordinate

    Returns:
        tuple of rounded pixel values.

    >>> lat_long_to_px(lat=35.255679, lng=139.740923) => (983, 2708)
    """
    x, y = sat(lng, lat, radians=False, errcheck=True)
    lng_px = round((x * 2.7188 / 5417) + 2750)
    lat_px = round(-(y * 2.709 / 5417)) + 2750
    return (lat_px, lng_px)


def px_to_km(lat_px=None, lng_px=None):
    """
    Converts px distance to km distance from center of image

    Args:
        lat_px (float): distance vertically from center of image (2750, 2750)
        lng_px (float): distance horizontally from center of image (2750, 2750)

    Returns:
        tuple: distance vertically from center in km, distance horizontally
            from center in km.
    """
    lat_km = (5417 * lat_px) / 2.70841 - (14896750 / 2.70841)
    lng_km = (5417 * lng_px) / 2.69165 - (14896750 / 2.69165)
    return (lat_km, lng_km)


def km_to_lat_lng(lat_km=None, lng_km=None):
    """
    Converts px distance to km distance from center of image

    Args:
        lat_km (float): distance vertically from center of image (2750, 2750)
        lng_km (float): distance horizontally from center of image (2750, 2750)

    Returns:
        tuple: real-life latitude and longitude coordinates.
    """
    lng, lat = sat(lng_km, lat_km, radians=False, errcheck=True, inverse=True)
    return(-lat, lng)


def px_to_lat_long(lat, lng):
    """ Convenience function to turn a px value from image to a lat, lng pair.

    For values toward the center of the map/image, it's accurate to a couple
    kms or so (alternatively, it is accurate to about 4 decimal places).
    Toward the edges of the map/image, it can be off by as much as +/-100km in
    the east/west direction.

    For example, Tokyo is pretty spot on; so is Melbourne. Honolulu is about
    95 km east of where it should be.

    >>> px_to_lat_long(983, 2708) => (35.25565506665156, 139.74090099964602)
    """
    try:
        lat, lng = px_to_km(lat, lng)
        lat, lng = km_to_lat_lng(lat, lng)
        return lat, lng
    except:
        return ("Space, Space")
