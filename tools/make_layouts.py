#!/usr/bin/env python3
"""Make the "layout" cover images for the service cards (same idea as the debut package image):
the artwork cut out with a white sticker outline, centred on a plum background with stars. No text.

Usage: python3 tools/make_layouts.py FONT_DIR
FONT_DIR must hold DMSerifDisplay-Regular.ttf and Poppins-SemiBold.ttf (Google Fonts, OFL).
Writes images/<name>.webp (1600x1200), images/t/ (520 wide) and images/s/ (360 wide).
"""
import os, sys, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'tools', 'fonts')
W, H = 1600, 1200

LAYOUTS = [
    # output name, source artwork, title, list (from DETAILS in index.html)
    ('vtuber-model-commission-cover', 'custom-vtuber-model-kitsune-gown', 'VTuber Model',
     ['Bust, half or full body', 'Layered PSD', 'Live2D rigging', 'VTube Studio ready', 'Updates at every stage']),
    ('pngtuber-commission-cover', 'custom-pngtuber-model-cat-mask', 'PNGTuber',
     ['Idle + talking states', 'Blinking', 'Transparent PNGs', 'Props included']),
    ('vtuber-pet-commission-cover', 'vtuber-pet-mascot-anglercat', 'VTuber Pet',
     ['Layered pet art', 'Optional Live2D rig', 'Transparent PNG']),
    ('chibi-vtuber-commission-cover', 'chibi-vtuber-model-witch', 'Chibi VTuber',
     ['Full-body chibi', '3 expressions', 'Layered, ready to rig']),
    ('custom-pfp-commission-cover', 'custom-vtuber-pfp-wolf', 'Custom PFP',
     ['Headshot to half body', 'High-resolution PNG', 'Simple background']),
    ('twitch-emotes-commission-cover', 'custom-twitch-emotes-witch', 'Emotes',
     ['Static or animated', 'Twitch & Discord sizes', 'Transparent PNG / GIF']),
]


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def cutout(path):
    """Remove the flat background that touches the edges (flood fill), keep everything else."""
    im = Image.open(path).convert('RGB')
    bg = im.getpixel((1, 1))
    w, h = im.size
    marker = (255, 0, 255)
    work = im.copy()
    for x in range(0, w, 8):
        for y in (0, h - 1):
            if sum(abs(a - b) for a, b in zip(work.getpixel((x, y)), bg)) < 40:
                ImageDraw.floodfill(work, (x, y), marker, thresh=34)
    for y in range(0, h, 8):
        for x in (0, w - 1):
            if sum(abs(a - b) for a, b in zip(work.getpixel((x, y)), bg)) < 40:
                ImageDraw.floodfill(work, (x, y), marker, thresh=34)
    diff = ImageChops.difference(work, Image.new('RGB', work.size, marker)).convert('L')
    alpha = diff.point(lambda v: 0 if v < 8 else 255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = im.convert('RGBA')
    out.putalpha(alpha)
    return out.crop(alpha.getbbox())


def sticker(art, border):
    """White outline + soft shadow around a cut-out."""
    pad = border * 3
    a = Image.new('L', (art.width + pad * 2, art.height + pad * 2), 0)
    a.paste(art.getchannel('A'), (pad, pad))
    grown = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(1.2))
    out = Image.new('RGBA', a.size, (0, 0, 0, 0))
    shadow = Image.new('RGBA', a.size, (40, 8, 30, 0))
    shadow.putalpha(grown.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .45)))
    out.alpha_composite(shadow, (0, 10))
    white = Image.new('RGBA', a.size, (255, 255, 255, 0))
    white.putalpha(grown)
    out.alpha_composite(white)
    out.alpha_composite(art, (pad, pad))
    return out


def star(d, cx, cy, r, fill):
    pts = []
    for i in range(8):
        rr = r if i % 2 == 0 else r * .28
        import math
        a = math.pi / 4 * i - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def background(seed):
    rnd = random.Random(seed)
    top, bot = (46, 28, 40), (122, 38, 84)
    bg = Image.new('RGB', (W, H))
    px = bg.load()
    for y in range(H):
        for x in range(0, W):
            t = min(1, max(0, (x * .35 + y) / (W * .35 + H)))
            px[x, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    bg = bg.convert('RGBA')
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((W * .2, H * .02, W * .8, H * .98), fill=(255, 140, 190, 120))
    g.ellipse((-W * .2, H * .55, W * .35, H * 1.3), fill=(201, 167, 255, 70))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    r = ImageDraw.Draw(ring)
    cx, cy, rad = int(W * .5), int(H * .5), int(H * .44)
    r.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=(255, 214, 230, 120), width=4)
    r.ellipse((cx - rad + 26, cy - rad + 26, cx + rad - 26, cy + rad - 26), fill=(255, 225, 238, 38))
    bg.alpha_composite(ring)
    d = ImageDraw.Draw(bg)
    for _ in range(46):
        x, y, s = rnd.randint(0, W), rnd.randint(0, H), rnd.choice([2, 2, 3, 4])
        d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 230, 240, rnd.randint(90, 200)))
    for _ in range(9):
        star(d, rnd.randint(40, W - 40), rnd.randint(40, H - 40), rnd.randint(10, 22), (255, 236, 244, 220))
    return bg


def card(title, items):
    tf, lf, sf = font('DMSerifDisplay-Regular.ttf', 74), font('Poppins-SemiBold.ttf', 38), font('Poppins-SemiBold.ttf', 26)
    cw = max(560, 150 + max(int(lf.getlength(t)) for t in items), 110 + int(tf.getlength(title)))
    ch = 64 + 92 + 30 + len(items) * 62 + 70
    c = Image.new('RGBA', (cw + 60, ch + 60), (0, 0, 0, 0))
    sh = Image.new('RGBA', c.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + cw, 40 + ch), 34, fill=(30, 6, 20, 110))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((30, 30, 30 + cw, 30 + ch), 34, fill=(255, 249, 243), outline=(255, 255, 255), width=6)
    d.rounded_rectangle((44, 44, 16 + cw, 16 + ch), 26, outline=(242, 98, 143, 90), width=3)
    d.text((80, 84), 'KEIKOARTS', font=sf, fill=(201, 58, 106))
    d.text((80, 118), title, font=tf, fill=(122, 40, 70))
    y = 118 + 92 + 30
    for it in items:
        d.ellipse((84, y + 16, 100, y + 32), fill=(242, 98, 143))
        d.text((118, y), it, font=lf, fill=(90, 35, 64))
        y += 62
    return c.rotate(3, resample=Image.BICUBIC, expand=True)


def make(name, src, title, items, seed):
    canvas = background(seed)
    art = cutout(os.path.join(ROOT, 'images', src + '.webp'))
    maxh, maxw = int(H * .9), int(W * .8)
    s = min(maxh / art.height, maxw / art.width)
    art = art.resize((int(art.width * s), int(art.height * s)), Image.LANCZOS)
    st = sticker(art, 12)
    x = int(W / 2 - st.width / 2)
    y = H - st.height + 30 if art.height > H * .8 else int(H / 2 - st.height / 2)
    canvas.alpha_composite(st, (x, y))   # no text on the cover (owner, Nov 2026); title and items stay in LAYOUTS for reference
    out = canvas.convert('RGB')
    out.save(os.path.join(ROOT, 'images', name + '.webp'), 'WEBP', quality=84, method=6)
    for folder, w in (('t', 520), ('s', 360)):
        out.resize((w, int(H * w / W)), Image.LANCZOS).save(os.path.join(ROOT, 'images', folder, name + '.webp'), 'WEBP', quality=80, method=6)
    print('made', name)


if __name__ == '__main__':
    for i, l in enumerate(LAYOUTS):
        make(*l, seed=i + 7)
