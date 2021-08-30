# A separate one-time executional custom file to generate gif image.

from PIL import Image, ImageDraw
import os

IMAGE_FOLDER = 'bot_images'


def get_wotv_elements():
    """Generate element names into a list with file naming conventions."""
    ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth',
                'Thunder', 'Water', 'Light', 'Dark']
    pref = 'wotv_'
    suf = '.png'
    return [f"{pref}{a.lower()}{suf}" for a in ELEMENTS]


def make_frame(image):
    """Process image into proper settings/masks for individual frame."""
    alp = image.getchannel('A')
    image = image.convert('RGB').convert('P', palette=Image.ADAPTIVE,
                                         colors=255)
    mask = Image.eval(alp, lambda a: 255 if a <=128 else 0)
    image.paste(255, mask)
    image.info['transparency'] = 255
    return image


def make_gif(size, path_list, gif_name):
    """Process list of image paths into gif of output name indicated."""
    images = [make_frame(Image.open(os.path.join(IMAGE_FOLDER, image_name)))
              for image_name in path_list]
    images[0].save(os.path.join(IMAGE_FOLDER, gif_name), 'GIF',
               save_all=True, append_images=images[1:], duration=500, loop=0)


if __name__ == '__main__':
    make_gif(58, get_wotv_elements(), 'wotv_elements.gif')
