from PIL import Image
import numpy as np
import os
from glob import glob
from wotv_png_paths import *
IMAGE_FOLDER = 'bot_images'
IMAGE_FOLDER_UNITS = 'unit_images'
PROCESSING_FOLDER = 'process_pending'

# a separate executional file to crop png files

def image_crop(im):
    # image cropping
    data = np.asarray(im)
    for i in range(data.shape[0]):
        if data[i, :, 3].sum() > 0:
            dim_0_start = i
            break
    else:
        dim_0_start = 0
    for i in range(data.shape[0] - 1, -1, -1):
        if data[i, :, 3].sum() > 0:
            dim_0_end = i
            break
    else:
        dim_0_end = data.shape[0]
    for i in range(data.shape[1]):
        if data[:, i, 3].sum() > 0:
            dim_1_start = i
            break
    else:
        dim_1_start = 0
    for i in range(data.shape[1] - 1, -1, -1):
        if data[:, i, 3].sum() > 0:
            dim_1_end = i
            break
    else:
        dim_1_end = data.shape[1]
    return Image.fromarray(data[dim_0_start:dim_0_end, dim_1_start:dim_1_end, :])

def image_convert(filepath, filename, save_folder=IMAGE_FOLDER):
    # image opening and saving
    im = Image.open(filepath)
    im = image_crop(im)
    im.save(os.path.join(save_folder, filename))
    print(f"{filename} saved.")

def image_crawl(folderpath):
    # find list of image paths
    return [f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f)) and '.png' in f]

def bot_folder_main():
    # scrapped function
    filelist = image_crawl(os.path.join(IMAGE_FOLDER, PROCESSING_FOLDER))
    for filename in filelist:
        image_convert(os.path.join(IMAGE_FOLDER, PROCESSING_FOLDER, filename), filename)

def all_units_main():
    # find all images to process
    filelist = glob(COLLABO_PATTERN) + glob(LAPIS_PATTERN)
    for filepath in filelist:
        filename = os.path.split(filepath)[1]
        # check if file already exists
        if not os.path.isfile(os.path.join(IMAGE_FOLDER_UNITS, filename)):
            image_convert(filepath, filename, IMAGE_FOLDER_UNITS)

if __name__ == '__main__':
    all_units_main()
