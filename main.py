from datetime import datetime, timedelta
import os
import os.path
import re
import glob
import fnmatch
import pytz
import sys
import piexif
import logging as log



RUNTIME_LOG_NAME = "runtime.log"
PRESUMED_TIMEZONE = pytz.timezone('America/Los_Angeles')
STRFTIME_EXIF_DATETIME = "%Y:%m:%d %H:%M:%S"
IMPORTED_FILE_LOG_NAME = 'imported_photos.log'
IMPORTED_FILE_LOG_PATH = os.path.join(os.path.dirname(__file__), IMPORTED_FILE_LOG_NAME)



log.basicConfig(filename=os.path.join(os.path.dirname(__file__), RUNTIME_LOG_NAME), level=log.DEBUG)


def make_mid_day(dt):
  return dt.replace(hour=12)


def insensitive_glob(pattern):
    def either(c):
        return '[%s%s]'%(c.lower(),c.upper()) if c.isalpha() else c
    return glob.glob(''.join(map(either,pattern)))


class FolderDateParseError(Exception):
  pass

class MissingOriginalDateTime(Exception):
  pass


# def get_proc_log_file():
#   if not _proc_file:
#     _proc_file = open(FILE_PROC_LOG_PATH, 'rw')
#   return _proc_file


# def write_to_proc_log(m)
#   get_proc_log_file().writeline(m)


def parse_folder_datetime(folder_path):
  folder_name = os.path.basename(folder_path)
  try:
    probable_folder_name_date = folder_name.split(',')[0]
  except IndexError:
    raise FolderDateParseError(folder_name)

  try:
    folder_datetime = make_mid_day(datetime.strptime(probable_folder_name_date, '%Y-%m-%d'))
  except ValueError:
    raise FolderDateParseError(probable_folder_name_date)

  return folder_datetime


def update_folder_images_exif_datetime_from_folder_name(folder_path):
  folder_datetime = parse_folder_datetime(folder_path)

  jpeg_image_paths = []
  for file in os.listdir(folder_path):
    if fnmatch.fnmatch(file, '*.[jJ][pP][eEgG]*'):
      jpeg_image_paths.append(os.path.join(folder_path, file))

  if len(jpeg_image_paths) == 0:
    log.warning("'%(folder_path)s' contains no images: skipping." % locals())
    return []

  try:
    base_image_datetime = get_image_original_datetime(jpeg_image_paths[0])

  except MissingOriginalDateTime:
    log.warning("'%(folder_path)s' images seem to have no exif data." % locals())
    update_images_exif_datetime(jpeg_image_paths, folder_datetime)

  else:
    time_diff = folder_datetime - base_image_datetime # How far off track is timediff

    if abs(time_diff) < timedelta(hours=24):
      log.warning("'%(folder_path)s' images seem to have correct exif data: skipping." % locals())
    
    else:
      log.warning("'%(folder_path)s' updating images by %(time_diff)s." % locals())
      update_images_exif_datetime(jpeg_image_paths, folder_datetime)

  return jpeg_image_paths


def get_image_original_datetime(image_path):
  exif_dict = piexif.load(image_path)

  if not exif_dict.get('Exif') or not piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
    raise MissingOriginalDateTime()

  dt_string = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]
  try:
    orig_dt = datetime.strptime(dt_string, STRFTIME_EXIF_DATETIME)
  except ValueError:
    raise MissingOriginalDateTime()

  return orig_dt


def update_images_exif_datetime(image_paths, new_dt):
  for image_path in image_paths:
    update_image_exif_datetime(image_path, new_dt)

def update_image_exif_datetime(image_path, new_dt):
  '''
  Update the exif data (in place) of the image specified at `image_path`
  '''
  log.warning("'%(image_path)s': should get %(new_dt)s" % locals())
  exif_dict = piexif.load(image_path)

  if exif_dict.get('Exif'): 
    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = new_dt.strftime(STRFTIME_EXIF_DATETIME)

  else:
    exif_dict['Exif'] = { piexif.ExifIFD.DateTimeOriginal: new_dt.strftime(STRFTIME_EXIF_DATETIME) }
    
  exif_bytes = piexif.dump(exif_dict)
  piexif.insert(exif_bytes, image_path)



def process_folders(folder_paths):
  all_jpegs = []
  for folder_path in folder_paths:
    log.warning('Processing folder: ' + folder_path)
    all_jpegs += update_folder_images_exif_datetime_from_folder_name(folder_path)
  return all_jpegs


def main():
  folder_paths = [x.strip() for x in sys.stdin.readlines()]
  all_jpegs = process_folders(folder_paths)

  with open(IMPORTED_FILE_LOG_PATH, 'a') as imported_file_log:

    for jpeg in all_jpegs:
      imported_file_log.writeline(jpef) # For cleanup later
      print jpeg # For the Automator script




if __name__ == '__main__':
  main()