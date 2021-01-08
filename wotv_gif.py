from PIL import Image, ImageDraw
import os
IMAGE_FOLDER = 'bot_images'

def get_wotv_elements():
    ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth', 'Thunder', 'Water', 'Light', 'Dark']
    pref = 'wotv_'
    suf = '.png'
    return [f"{pref}{a.lower()}{suf}" for a in ELEMENTS]

def make_frame(im):
    alp = im.getchannel('A')
    im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
    mask = Image.eval(alp, lambda a: 255 if a <=128 else 0)
    im.paste(255, mask)
    im.info['transparency'] = 255
    return im

def make_gif(size, imlist, gifname):
    images = [make_frame(Image.open(os.path.join(IMAGE_FOLDER, imname))) for imname in imlist]
    images[0].save(os.path.join(IMAGE_FOLDER, gifname), 'GIF',
               save_all=True, append_images=images[1:], duration=500, loop=0)

make_gif(58, get_wotv_elements(), 'wotv_elements.gif')
