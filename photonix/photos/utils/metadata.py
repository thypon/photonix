import os
import re
from subprocess import Popen, PIPE
from datetime import datetime
from dateutil.parser import parse as parse_date

from django.utils.timezone import utc


class PhotoMetadata(object):
    def __init__(self, path):
        self.data = {}
        try:
            result = Popen(['exiftool', path], stdout=PIPE, stdin=PIPE, stderr=PIPE).communicate()[0].decode('utf-8')
        except UnicodeDecodeError:
            result = ''
        for line in str(result).split('\n'):
            if line:
                try:
                    k, v = line.split(':', 1)
                    self.data[k.strip()] = v.strip()
                except ValueError:
                    pass

    def get(self, attribute):
        return self.data.get(attribute)

    def get_all(self):
        return self.data


def parse_datetime(date_str):
    if not date_str:
        return None
    if '.' in date_str:
        date_str = date_str.split('.', 1)[0]
    try:
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').replace(tzinfo=utc)
    except ValueError:
        parsed_date = parse_date(date_str)
        if not parsed_date.tzinfo:
            parsed_date = parsed_date.replace(tzinfo=utc)
        return parsed_date


def parse_gps_location(gps_str):
    # 50 deg 49' 9.53" N, 0 deg 8' 13.33" W
    regex = r'''(\d{1,3}) deg (\d{1,2})' (\d{1,2}).(\d{2})" ([N,S]), (\d{1,3}) deg (\d{1,2})' (\d{1,2}).(\d{2})" ([E,W])'''
    m = re.search(regex, gps_str)

    latitude = float(m.group(1)) + (float(m.group(2)) / 60) + (float('{}.{}'.format(m.group(3), m.group(4))) / 60 / 100)
    if m.group(5) == 'S':
        latitude *= -1

    longitude = float(m.group(6)) + (float(m.group(7)) / 60) + (float('{}.{}'.format(m.group(8), m.group(9))) / 60 / 100)
    if m.group(10) == 'W':
        longitude *= -1

    return (latitude, longitude)


def get_datetime(path):
    '''
    Tries to get date/time from EXIF data which works on JPEG and raw files.
    Failing it that it tries to find the date in the filename.
    '''
    # TODO: Use 'GPS Date/Time' if available as it's more accurate

    # First try the date in the metadate
    metadata = PhotoMetadata(path)
    date_str = metadata.get('Date/Time Original')
    if date_str:
        return parse_datetime(date_str)

    # If there was not date metadata, try to infer it from filename
    fn = os.path.split(path)[1]
    matched = re.search(r'((19|20)[0-9]{2})-([0-9]{2})-([0-9]{2})\D', fn)
    if not matched:
        matched = re.search(r'\D((19|20)[0-9]{2})([0-9]{2})([0-9]{2})\D', fn)
    if matched:
        # import pdb; pdb.set_trace()
        date_str = '{}-{}-{}'.format(matched.group(1), matched.group(3), matched.group(4))
        return datetime.strptime(date_str, '%Y-%m-%d')
    return None


def get_dimensions(path):
    metadata = PhotoMetadata(path)
    if metadata.data.get('Image Width') and metadata.data.get('Image Height'):
        return (int(metadata.data['Image Width']), int(metadata.data['Image Height']))
    return (None, None)

def get_mimetype(path):
    # Done
    """Pulls the MIME Type from the given path"""
    metadata = PhotoMetadata(path)
    if metadata.data.get('MIME Type'):
        return metadata.data.get('MIME Type')
    return None
