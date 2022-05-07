# A separate one-time executional custom file to generate gif image.

from PIL import Image, ImageDraw
import os

from wotv_png_process import image_crop

IMAGE_FOLDER = 'bot_images'


def get_wotv_heartquartzs():
    """Generate a list of file paths for heartquartzs."""
    HEARTQUARTZS = ['ur', 'ssr', 'sr', 'r']
    pref = os.path.join('process_pending', 'it_af_mat_6_')
    suf = '.png'
    return [f"{pref}{a}{suf}" for a in HEARTQUARTZS]


def get_wotv_materias():
    """Generate a list of file paths for materias."""
    MATERIAS = ['f', 'h', 'i', 'o', 's', 'w']
    pref = os.path.join('process_pending', 'it_aw_mt_')
    suf = '_sr.png'
    return [f"{pref}{a}{suf}" for a in MATERIAS]


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


def make_gif(path_list, gif_name):
    """Process list of image paths into gif of output name indicated."""
    images = [make_frame(
                image_crop(Image.open(os.path.join(IMAGE_FOLDER, image_name)))
              ) for image_name in path_list]
    images[0].save(os.path.join(IMAGE_FOLDER, gif_name), 'GIF',
               save_all=True, append_images=images[1:], duration=500, loop=0)


if __name__ == '__main__':
    # make_gif(get_wotv_elements(), 'wotv_elements.gif')
    # make_gif(get_wotv_materias(), 'wotv_materias.gif')
    # for image_name in get_wotv_heartquartzs():
    #     image_crop(Image.open(os.path.join(IMAGE_FOLDER, image_name))).save(os.path.join(IMAGE_FOLDER, image_name))

    make_gif(get_wotv_heartquartzs(), 'wotv_heartquartzs.gif')
