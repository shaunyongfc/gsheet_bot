# A separate executional file to crop png files from assets folder.
# Updated to only generate if files do not already exist.

from PIL import Image
import numpy as np
import os
from glob import glob

from wotv_png_paths import LAPIS_PATTERN, COLLABO_PATTERN
# Private file containing absolute path patterns to certain folders.

IMAGE_FOLDER = 'bot_images'
IMAGE_FOLDER_UNITS = 'unit_images'
PROCESSING_FOLDER = 'process_pending'


def image_crop(input_image):
    """Take image object input, crop transparent borders,
    and return image object output.
    """
    image_data = np.asarray(input_image)
    for i in range(image_data.shape[0]):
        if image_data[i, :, 3].sum() > 0:
            dim_0_start = i
            break
    else:
        dim_0_start = 0
    for i in range(image_data.shape[0] - 1, -1, -1):
        if image_data[i, :, 3].sum() > 0:
            dim_0_end = i
            break
    else:
        dim_0_end = image_data.shape[0]
    for i in range(image_data.shape[1]):
        if image_data[:, i, 3].sum() > 0:
            dim_1_start = i
            break
    else:
        dim_1_start = 0
    for i in range(image_data.shape[1] - 1, -1, -1):
        if image_data[:, i, 3].sum() > 0:
            dim_1_end = i
            break
    else:
        dim_1_end = image_data.shape[1]
    return Image.fromarray(image_data[dim_0_start:dim_0_end, dim_1_start:dim_1_end, :])


def image_convert(file_path: 'Full file path to input image.',
                  filename: 'File name to be saved.',
                  save_folder: 'Path to saved image.' = IMAGE_FOLDER):
    """Take image file path input, open the image, process,
    and save cropped image into specified file path and name.
    """
    image = Image.open(file_path)
    image = image_crop(image)
    image.save(os.path.join(save_folder, filename))
    print(f"{filename} saved.")


def image_crawl(folder_path):
    """Crawl all png images in the folder and
    return the list of full file paths in the folder.
    (Not used in main execution.)
    """
    return [f for f in os.listdir(folder_path) \
        if os.path.isfile(os.path.join(folder_path, f)) and '.png' in f]


def bot_folder_main():
    """Crawl all png images in a specified process-pending folders
    and save cropped images in another specified folder.
    """
    filelist = image_crawl(os.path.join(IMAGE_FOLDER, PROCESSING_FOLDER))
    for filename in filelist:
        image_convert(os.path.join(IMAGE_FOLDER, PROCESSING_FOLDER, filename),
                      filename)


def wotv_all_units():
    """Crawl all png images matching specified patterns and
    save cropped images in a specified folder.
    """
    filelist = glob(COLLABO_PATTERN) + glob(LAPIS_PATTERN)
    for filepath in filelist:
        filename = os.path.split(filepath)[1]
        # Check if target file is already processed and already exists.
        if not os.path.isfile(os.path.join(IMAGE_FOLDER_UNITS, filename)):
            image_convert(filepath, filename, IMAGE_FOLDER_UNITS)


if __name__ == '__main__':
    wotv_all_units()
