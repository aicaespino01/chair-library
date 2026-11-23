#!/usr/bin/env python3
"""Make the short ChairTok videos (videos/<chair id>.mp4) from our own chair photos.

Run from the library folder:  python3 website/make_videos.py [chair-id ...]
Every fact shown in a video is written in VIDEOS below and was copied from that chair's file
(chairs/<id>.md). When a chair file changes, update its entry here and run this again.
Needs: Python 3 with Pillow and numpy, ffmpeg, and the Inter + Noto Color Emoji fonts.
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'videos')
W, H, FPS = 720, 1280, 30
FONT_DIR = '/usr/share/fonts/opentype/inter/'
EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-r', str(FPS)]

PINK, CYAN, GREEN = (254, 44, 85), (37, 244, 238), (34, 197, 94)
BRAND = {'Okamura': (232, 80, 91), 'Kokuyo': (61, 139, 253), 'Itoki': (20, 184, 166)}

# ---------- the videos: one entry per chair, facts copied from the chair files ----------
VIDEOS = {
    'okamura-sulato-c342gr': {
        'brand': 'Okamura',
        'hero': ('okamura-sulato-c342gr-2.jpg', (0.5, 0.5)),
        'title': 'Sulato', 'name': 'Okamura Sulato', 'code': 'C342GR',
        'sub': 'Low back · arms · coat hanger',
        'price': '₱5,500',
        'facts': [
            ('okamura-sulato-c342gr-2.jpg', (0.5, 0.75), '📏', 'Seat 42–51.2 cm high', 'Lowest 42 cm: at 150 cm tall you may need a footrest'),
            ('okamura-sulato-c342gr-2.jpg', (0.55, 0.55), '😌', 'Comfy seat', '3 firmness zones, and a 20° recline that locks at any angle'),
            ('okamura-sulato-c342gr-label.jpg', (0.5, 0.55), '🏷️', 'Made in 2021', 'Clear Okamura label: about 3 of its 8-year service life used'),
            ('okamura-sulato-c342gr-2.jpg', (0.3, 0.3), '🧥', 'Arms + coat hanger', 'The arms are fixed: they don’t move up or down'),
        ],
        'pros': ['Model confirmed by the label', 'Arms and a coat hanger', 'Fairly recent (2021)'],
        'cons': ['No seat-depth slide', 'Fixed arms', 'Fabric is warmer than mesh'],
        'end': [('Price here', '₱5,500'), ('New in Japan', '≈ ₱36,400'), ('Value', 'Fair · 15% of new')],
        'where': 'Office Busters PH',
        'cons_photo': ('okamura-sulato-c342gr-1.jpg', (0.5, 0.5)),
    },
    'itoki-spina-ke-757gp': {
        'brand': 'Itoki',
        'hero': ('itoki-spina-1.jpg', (0.5, 0.45)),
        'title': 'Spina', 'name': 'Itoki Spina', 'code': 'KE-757GP',
        'sub': 'Rubbery rib back · high-end',
        'price': 'Price: ask',
        'facts': [
            ('itoki-spina-1.jpg', (0.5, 0.2), '🌬️', 'Rib back', 'Soft rubber-like ribs let air through: cooler than cloth'),
            ('itoki-spina-2.jpg', (0.5, 0.4), '🪄', 'Automatic lumbar', 'Sit down: the seat slides back and the lower back pushes forward'),
            ('itoki-spina-1.jpg', (0.5, 0.7), '📏', 'Seat 40–51.6 cm high', 'Low 40 cm minimum: good for shorter people'),
            ('itoki-spina-2.jpg', (0.6, 0.8), '🏷️', 'Made in 2009', 'Lot 090331 on the label: about 17 years old'),
            ('itoki-spina-2.jpg', (0.3, 0.6), '💪', 'Arms adjust', 'Up and down 95 mm, and turn inward 20°'),
        ],
        'pros': ['Automatic lumbar and seat', 'Breathable rib back', 'Low seat: 40 cm'],
        'cons': ['About 17 years old: check the gas lift', 'Seat may feel thin (1 review)', 'No headrest'],
        'end': [('Price here', 'not stated yet'), ('New in Japan', '¥140,200 ≈ ₱56,200'), ('Value', 'ask the price first')],
        'where': 'Office Busters PH',
    },
    'kokuyo-legno2-crs-g210f4vrb4': {
        'brand': 'Kokuyo',
        'hero': ('kokuyo-legno2-crs-g210f4vrb4-1.jpg', (0.55, 0.35)),
        'title': 'LEGNO2', 'name': 'Kokuyo LEGNO2', 'code': 'CRS-G210F4VRB4',
        'sub': 'Simple basic chair · gray shell',
        'price': 'Price: ask',
        'facts': [
            ('kokuyo-legno2-crs-g210f4vrb4-1.jpg', (0.5, 0.6), '📏', 'Seat 40.5–51.5 cm high', 'Seat depth 45.5 cm'),
            ('kokuyo-legno2-crs-g210f4vrb4-1.jpg', (0.3, 0.5), '🪶', 'Light: 9.5 kg', 'Kokuyo’s simple basic office chair'),
            ('kokuyo-legno2-crs-g210f4vrb4-1.jpg', (0.7, 0.4), '⚖️', 'Weight limit 80 kg', 'From a Japanese shop listing'),
            ('kokuyo-legno2-crs-g210f4vrb4-1.jpg', (0.55, 0.3), '🏷️', 'Made in 2009', 'Lot 090630 on the label: about 17 years old'),
        ],
        'pros': ['Model confirmed by the label', 'All sizes published', 'Light and simple'],
        'cons': ['80 kg weight limit', 'No lumbar adjustment', 'Old unit (2009)'],
        'end': [('Price here', 'not stated yet'), ('New in Japan', '≈ ₱11,900 (shop price)'), ('Value', 'ask the price first')],
        'where': 'Office Busters PH',
    },
}

HERO_S, FACT_S, LIST_S, END_S = 3.6, 3.4, 4.2, 4.0

# ---------- drawing helpers ----------
_fonts = {}
def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + 'Inter-' + weight + '.otf', size)
    return _fonts[key]

_emoji = {}
def emoji(ch, size):
    if (ch, size) not in _emoji:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor='mm')
        im = im.crop(im.getbbox())
        r = size / max(im.size)
        _emoji[(ch, size)] = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
    return _emoji[(ch, size)]

def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def text_box(text, f, fg, bg, maxw, pad=(22, 14), radius=18, align='center'):
    """Rounded TikTok-style text sticker."""
    lines = wrap(text, f, maxw)
    asc, desc = f.getmetrics()
    lh = asc + desc + 4
    tw = max(f.getlength(l) for l in lines)
    im = Image.new('RGBA', (int(tw + 2 * pad[0]), int(lh * len(lines) + 2 * pad[1])), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius, fill=bg)
    for i, l in enumerate(lines):
        x = (im.width - f.getlength(l)) / 2 if align == 'center' else pad[0]
        d.text((x, pad[1] + i * lh), l, font=f, fill=fg)
    return im

def cover_canvas(photo, focus, zoom_room=1.18):
    """A 9:16 picture bigger than the frame (room to zoom): photo over a blurred copy of itself."""
    im = Image.open(os.path.join(ROOT, 'photos', photo)).convert('RGB')
    cw, ch = int(W * zoom_room), int(H * zoom_room)
    bg = im.copy()
    s = max(cw / bg.width, ch / bg.height)
    bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1), Image.BILINEAR)
    bg = bg.crop(((bg.width - cw) // 2, (bg.height - ch) // 2, (bg.width - cw) // 2 + cw, (bg.height - ch) // 2 + ch))
    bg = bg.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.6))
    # tall photos fill the frame; wide ones sit in the middle on the blur
    s2 = max(cw / im.width, ch / im.height) if im.height / im.width > 1.25 else cw / im.width
    fg = im.resize((int(im.width * s2), int(im.height * s2)), Image.LANCZOS)
    x = int((cw - fg.width) * focus[0]) if fg.width > cw else (cw - fg.width) // 2
    y = int((ch - fg.height) * focus[1]) if fg.height > ch else (ch - fg.height) // 2
    bg.paste(fg, (x, y))
    return bg

def zoom_frame(canvas, p, zin=True, drift=(0, 0)):
    """Smooth Ken Burns: crop a shrinking (or growing) box and scale it to the frame."""
    e = 0.5 - 0.5 * math.cos(math.pi * p)
    z = (1.0 + 0.10 * e) if zin else (1.10 - 0.10 * e)
    bw, bh = canvas.width / (z * 1.18) * 1.0, canvas.height / (z * 1.18)
    cx = canvas.width / 2 + drift[0] * e * canvas.width * 0.04
    cy = canvas.height / 2 + drift[1] * e * canvas.height * 0.04
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    return canvas.resize((W, H), Image.BILINEAR, box=box)

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def put(frame, layer, x, y, t, start, dur=0.35, rise=26, pop=False):
    """Fade + slide (or pop) a layer in at time `start`."""
    if t < start: return
    k = ease_out((t - start) / dur)
    lay = layer
    if pop and k < 1:
        sc = 0.6 + 0.4 * (1 + 0.25 * math.sin(k * math.pi)) * k + 0.0
        sc = max(0.05, min(1.12, 0.6 + 0.52 * k))
        lay = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
        x += (layer.width - lay.width) // 2; y += (layer.height - lay.height) // 2
    if k < 1:
        a = lay.getchannel('A').point(lambda v: int(v * k))
        lay = lay.copy(); lay.putalpha(a)
    frame.alpha_composite(lay, (int(x), int(y + (0 if pop else rise * (1 - k)))))

def shade(frame, top=True, bottom=True):
    g = Image.new('L', (1, 256))
    for i in range(256): g.putpixel((0, i), int(170 * (i / 255) ** 1.6))
    if bottom:
        m = g.resize((W, 520)); blk = Image.new('RGBA', (W, 520), (0, 0, 0, 255)); blk.putalpha(m)
        frame.alpha_composite(blk, (0, H - 520))
    if top:
        m = g.transpose(Image.FLIP_TOP_BOTTOM).resize((W, 260)); blk = Image.new('RGBA', (W, 260), (0, 0, 0, 255)); blk.putalpha(m)
        frame.alpha_composite(blk, (0, 0))

# Text stays inside x 70..620 so the ChairTok buttons on the right never cover it.
SAFE_L, SAFE_R = 70, 620
def cx(layer): return SAFE_L + (SAFE_R - SAFE_L - layer.width) // 2

# ---------- scenes ----------
def scene_hero(v):
    canvas = cover_canvas(*v['hero'])
    col = BRAND[v['brand']]
    pill = text_box(v['brand'].upper(), font('Black', 30), (255, 255, 255), col + (255,), 500, pad=(20, 8), radius=24)
    title = text_box(v['title'], font('Black', 62), (22, 24, 35), (255, 255, 255, 255), 520, pad=(24, 12))
    code = text_box(v['code'], font('Bold', 34), (255, 255, 255), (0, 0, 0, 165), 520, pad=(18, 8), radius=14)
    sub = text_box(v['sub'], font('SemiBold', 32), (255, 255, 255), (0, 0, 0, 165), 520, pad=(18, 10), radius=14)
    price = text_box(v['price'], font('Black', 58), (255, 255, 255), PINK + (255,), 520, pad=(26, 10), radius=16)
    tick = text_box('Model confirmed', font('Bold', 28), (12, 60, 30), (190, 245, 205, 255), 520, pad=(16, 8), radius=20)
    tick_e = emoji('✅', 30)
    y0 = 250
    def draw(t, p):
        f = zoom_frame(canvas, p, True, (0, -0.3)).convert('RGBA'); shade(f)
        y = y0
        put(f, pill, cx(pill), y, t, 0.10); y += pill.height + 16
        put(f, title, cx(title), y, t, 0.25); y += title.height + 12
        put(f, code, cx(code), y, t, 0.40); y += code.height + 10
        put(f, sub, cx(sub), y, t, 0.55); y += sub.height + 30
        put(f, price, cx(price), y, t, 0.95, dur=0.4, pop=True); y += price.height + 24
        tw = tick.width + tick_e.width + 10
        put(f, tick_e, SAFE_L + (SAFE_R - SAFE_L - tw) // 2, y + (tick.height - tick_e.height) // 2, t, 1.4)
        put(f, tick, SAFE_L + (SAFE_R - SAFE_L - tw) // 2 + tick_e.width + 10, y, t, 1.4)
        return f
    return HERO_S, draw

def scene_fact(fact, i, n):
    photo, focus, em, head, sub = fact
    canvas = cover_canvas(photo, focus)
    e = emoji(em, 110)
    headl = text_box(head, font('Black', 48), (22, 24, 35), (255, 255, 255, 255), 540, pad=(22, 14))
    subl = text_box(sub, font('SemiBold', 33), (255, 255, 255), (0, 0, 0, 170), 500, pad=(20, 12), radius=14)
    count = text_box(f'{i}/{n}', font('Bold', 24), (255, 255, 255), (0, 0, 0, 120), 200, pad=(12, 6), radius=12)
    zin = i % 2 == 1
    def draw(t, p):
        f = zoom_frame(canvas, p, zin, (0.5 if zin else -0.5, 0)).convert('RGBA'); shade(f)
        y = 300
        put(f, e, cx(e), y, t, 0.05, pop=True); y += e.height + 22
        put(f, headl, cx(headl), y, t, 0.25); y += headl.height + 14
        put(f, subl, cx(subl), y, t, 0.55)
        put(f, count, SAFE_R - count.width, 200, t, 0.0, dur=0.2, rise=0)
        return f
    return FACT_S, draw

def scene_list(photo, focus, title, em, items, color):
    canvas = cover_canvas(photo, focus)
    canvas = canvas.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.55))
    e = emoji(em, 70)
    head = text_box(title, font('Black', 52), (255, 255, 255), color + (255,), 520, pad=(24, 12))
    rows = [text_box(x, font('Bold', 36), (22, 24, 35), (255, 255, 255, 245), 500, pad=(22, 14), radius=16) for x in items]
    def draw(t, p):
        f = zoom_frame(canvas, p, True).convert('RGBA')
        y = 290
        put(f, e, cx(e), y, t, 0.05, pop=True); y += e.height + 18
        put(f, head, cx(head), y, t, 0.2); y += head.height + 34
        for k, r in enumerate(rows):
            put(f, r, cx(r), y, t, 0.6 + 0.55 * k); y += r.height + 18
        return f
    return LIST_S, draw

def scene_end(v):
    canvas = cover_canvas(*v['hero'])
    canvas = canvas.filter(ImageFilter.GaussianBlur(18)).point(lambda v_: int(v_ * 0.45))
    card = Image.new('RGBA', (520, 120 + 92 * len(v['end'])), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card.width - 1, card.height - 1], 28, fill=(255, 255, 255, 250))
    d.text((card.width // 2, 54), v['name'], font=font('Black', 40), fill=(22, 24, 35), anchor='mm')
    for k, (lab, val) in enumerate(v['end']):
        yy = 110 + 92 * k
        d.line([(36, yy - 10), (card.width - 36, yy - 10)], fill=(230, 230, 235), width=2)
        d.text((40, yy + 6), lab, font=font('SemiBold', 26), fill=(110, 110, 120))
        valf = font('Black', 34)
        val = val if valf.getlength(val) < card.width - 80 else val
        d.text((40, yy + 38), val, font=valf, fill=PINK if k == 0 else (22, 24, 35))
    where = text_box('📍', font('Bold', 30), (255, 255, 255), (0, 0, 0, 0), 500)
    wtxt = text_box(v['where'], font('Bold', 32), (255, 255, 255), (0, 0, 0, 160), 500, pad=(18, 10), radius=14)
    pin = emoji('📍', 38)
    follow = text_box('Swipe up for the next chair', font('Bold', 30), (255, 255, 255), PINK + (255,), 520, pad=(22, 12), radius=22)
    up = emoji('👆', 44)
    def draw(t, p):
        f = zoom_frame(canvas, p, False).convert('RGBA')
        y = 240
        put(f, card, cx(card), y, t, 0.1, pop=True); y += card.height + 30
        tw = pin.width + 10 + wtxt.width
        put(f, pin, SAFE_L + (SAFE_R - SAFE_L - tw) // 2, y + (wtxt.height - pin.height) // 2, t, 0.6)
        put(f, wtxt, SAFE_L + (SAFE_R - SAFE_L - tw) // 2 + pin.width + 10, y, t, 0.6); y += wtxt.height + 40
        bob = int(8 * math.sin(t * 5))
        put(f, up, cx(up), y + bob, t, 1.2, rise=0); y += up.height + 12
        put(f, follow, cx(follow), y, t, 1.2)
        return f
    return END_S, draw

# ---------- music: a soft, cute plucked loop made from scratch (no outside music) ----------
def music(seconds, path, seed=0):
    sr = 44100; n = int(sr * seconds); out = np.zeros(n)
    bpm = 104; beat = 60 / bpm
    prog = [(60, 64, 67), (57, 60, 64), (53, 57, 60), (55, 59, 62)]  # C Am F G
    melody = [72, 76, 79, 76, 74, 72, 69, 72, 69, 72, 76, 74, 71, 74, 79, 76]
    rng = np.random.default_rng(seed)
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    def pluck(start, m, dur, vol):
        i0 = int(start * sr); L = int(dur * sr)
        if i0 >= n: return
        L = min(L, n - i0); tt = np.arange(L) / sr; f = hz(m)
        env = np.exp(-tt * 5.5) * np.minimum(1, tt * 400)
        out[i0:i0 + L] += vol * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) + 0.1 * np.sin(6 * np.pi * f * tt))
    t = 0.0; bar = 0
    while t < seconds:
        chord = prog[bar % 4]
        for b in range(4):
            for k, m in enumerate(chord):
                pluck(t + b * beat + k * 0.012, m - 12 if b % 2 == 0 and k == 0 else m, beat * 1.6, 0.07)
            mi = (bar * 4 + b) % len(melody)
            if (bar * 4 + b) % 2 == 0 or rng.random() < 0.5:
                pluck(t + b * beat, melody[mi], beat * 1.2, 0.10)
            # soft shaker on the off-beat
            i0 = int((t + b * beat + beat / 2) * sr); L = int(0.05 * sr)
            if i0 + L < n:
                out[i0:i0 + L] += 0.025 * rng.standard_normal(L) * np.exp(-np.arange(L) / sr * 80)
        t += 4 * beat; bar += 1
    fade = int(1.2 * sr); out[-fade:] *= np.linspace(1, 0, fade); out[:int(0.05 * sr)] *= np.linspace(0, 1, int(0.05 * sr))
    out = out / (np.abs(out).max() + 1e-9) * 0.55
    data = (out * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data.tobytes())

# ---------- render ----------
def scenes_for(v):
    s = [scene_hero(v)]
    n = len(v['facts'])
    for i, fct in enumerate(v['facts'], 1): s.append(scene_fact(fct, i, n))
    last = v.get('cons_photo') or v['facts'][-1][:2]
    s.append(scene_list(v['hero'][0], v['hero'][1], 'The good', '💚', v['pros'], GREEN))
    s.append(scene_list(last[0], last[1], 'Watch out', '👀', v['cons'], PINK))
    s.append(scene_end(v))
    return s

def render_scene(draw, dur, path):
    tmp = path[:-4] + '.part.mp4'
    nf = int(round(dur * FPS))
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *ENC, tmp], stdin=subprocess.PIPE)
    for k in range(nf):
        fr = draw(k / FPS, k / max(1, nf - 1)).convert('RGB')
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit('ffmpeg failed on ' + path)
    os.replace(tmp, path)

def make(cid, frames_only=False):
    v = VIDEOS[cid]
    work = os.path.join('/tmp', 'chairtok-' + cid); os.makedirs(work, exist_ok=True)
    scenes = scenes_for(v)
    if frames_only:
        for i, (dur, draw) in enumerate(scenes):
            draw(dur * 0.8, 0.8).convert('RGB').save(os.path.join(work, f'frame-{i}.jpg'), quality=90)
        return work
    parts = []
    for i, (dur, draw) in enumerate(scenes):
        part = os.path.join(work, f'scene-{i:02d}.mp4'); render_scene(draw, dur, part); parts.append(part)
    total = sum(d for d, _ in scenes)
    lst = os.path.join(work, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    silent = os.path.join(work, 'joined.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    wav = os.path.join(work, 'music.wav'); music(total, wav, seed=sum(map(ord, cid)))
    os.makedirs(OUT_DIR, exist_ok=True)
    final = os.path.join(OUT_DIR, cid + '.mp4'); tmp = final[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '96k', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, final)
    # poster: the hero frame once everything is on screen
    scenes[0][1](HERO_S * 0.9, 0.9).convert('RGB').save(os.path.join(OUT_DIR, cid + '.jpg'), quality=84)
    return final

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = '--frames' in sys.argv
    for cid in (args or list(VIDEOS)):
        print(make(cid, frames_only=frames))
