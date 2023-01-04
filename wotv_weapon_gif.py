# A separate one-time executional custom file to generate gif image.

from PIL import Image, ImageOps
import os
import glob


IMAGE_FOLDER = 'bot_images'


def make_frame(image):
    """Process image into proper settings/masks for individual frame."""
    alp = image.getchannel('A')
    image = image.convert('RGB').convert('P', palette=Image.Palette.ADAPTIVE,
                                         colors=255)
    mask = Image.eval(alp, lambda a: 255 if a <=128 else 0)
    image.paste(255, mask)
    image.info['transparency'] = 0
    return image


def make_gif(path_list, gif_name, duration=1000):
    """Process list of image paths into gif of output name indicated."""
    images = [make_frame(Image.open(image_path)) for image_path in path_list]
    images[0].save(os.path.join(IMAGE_FOLDER, gif_name), 'GIF',
               save_all=True, append_images=images[1:], duration=duration,
               loop=0, disposal=2)
    print(f"{os.path.join(IMAGE_FOLDER, gif_name)} saved.")


def check_dimensions():
    """Find the largest image size of each side for all job icons."""
    width = 0
    height = 0
    path_list = glob.glob(f"{os.path.join('wotv_jobs', 'weapon_')}*.png")
    for path in path_list:
        im = Image.open(path)
        if im.size[0] > width:
            width = im.size[0]
        if im.size[1] > height:
            height = im.size[1]
    return width, height


def expand_images(width, height):
    """Find all images in the folder and expand them to the same size."""
    for path in glob.glob(f"{os.path.join('wotv_jobs', 'weapon_')}*.png"):
        im = Image.open(path)
        width_pad = (width - im.size[0]) // 2
        height_pad = (height - im.size[1]) // 2
        im = ImageOps.expand(im, (
            width_pad,
            height_pad,
            width - width_pad - im.size[0],
            height - height_pad - im.size[1],
        ))
        im.save(path.replace('wotv_jobs', 'wotv_jobs_padded'))
        print(f"{path} expanded.")


def make_weapon_gif():
    """Make a GIF for each job category in relation to job VCs in WOTV."""
    WEAPONS = ['axe', 'book', 'bow', 'dagger', 'fist', 'glove', 'gs', 'gun',
               'katana', 'mace', 'nb', 'spear', 'staffa', 'staffb', 'sworda',
               'swordb', 'swordc',]
    for weapon in WEAPONS:
        path_list = glob.glob(f"{os.path.join('wotv_jobs_padded', 'weapon_')}{weapon}_*.png")
        make_gif(path_list, f"wotv_w_{weapon}.gif")


if __name__ == '__main__':
    width, height = check_dimensions()
    expand_images(width, height)
    make_weapon_gif()
