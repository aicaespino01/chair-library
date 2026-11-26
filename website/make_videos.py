#!/usr/bin/env python3
"""ChairTok videos: 21 chairs, 12 different TikTok formats (incl. "we have X at home"), each with its own look and its own music.

Run from the library folder, after `node website/build.js`:
    python3 website/make_videos.py              # all videos in PLAN
    python3 website/make_videos.py <chair-id>   # one video (or a format name, e.g. "news")
    python3 website/make_videos.py --frames     # test frames only (no video), in /tmp/chairtok-frames
Facts come from the chair files (through the built website data), so they match the library.
Jokes, hype and narration are clearly for fun; prices, sizes and flaws are the real ones from the files.
All music and sound effects are made here from scratch (no songs, no samples).
Needs: Python 3 with Pillow and numpy, ffmpeg, the Inter, DejaVu and Noto Color Emoji fonts.
"""
import json, math, os, random, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'videos')
W, H, FPS = 720, 1280, 30
SR = 44100
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p', '-r', str(FPS)]
INTER = '/usr/share/fonts/opentype/inter/Inter-%s.otf'
SERIF_I = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf'
SERIF_B = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
POPLITEAL = 40.6  # the buyer's popliteal height in cm (from the chair search brief)

# which chair gets which format (formats are spread out so neighbours in the feed differ)
PLAN = [
    ('okamura-feego-mesh-cj51br', 'athome'),
    ('okamura-sulato-c342gr', 'salesman'),
    ('unidentified-ob-okamura-ckz', 'mystery'),
    ('okamura-sylphy-c638xr', 'brainrot'),
    ('itoki-spina-ke-757gp', 'documentary'),
    ('kokuyo-legno2-crs-g210f4vrb4', 'nervous'),
    ('steelcase-leap', 'aislop'),
    ('okamura-escudo-mesh', 'spin'),
    ('okamura-fluent-cb31zr', 'news'),
    ('unidentified-ob-okamura-blue-adjustable-arms', 'brainrot'),
    ('xpanse-f7', 'pov'),
    ('unidentified-ob-okamura-c445zr', 'mystery'),
    ('kokuyo-m4-cr-g2201', 'dating'),
    ('plus-nexis-c02-kc-nx616', 'jokes'),
    ('uchida-epo', 'nervous'),
    ('okamura-carrozza-ck33', 'brainrot'),
    ('itoki-prego-kz-435cg', 'spin'),
    ('kokuyo-legno2-cr-g211', 'documentary'),
    ('unidentified-ob-black-leather-loop-arm', 'salesman'),
    ('itoki-torte-r-kz-246', 'pov'),
    ('unidentified-ob-kokuyo-cro', 'mystery'),
]

BRAND_COL = {'Okamura': (232, 80, 91), 'Kokuyo': (61, 139, 253), 'Itoki': (20, 184, 166), 'Plus': (168, 85, 247),
             'Steelcase': (245, 158, 11), 'Uchida': (236, 72, 153), 'XPANSE': (99, 102, 241)}
ALL_DATA = {}  # every chair, for formats that show a second chair
PINK, CYAN, YEL, GRN = (254, 44, 85), (37, 244, 238), (255, 214, 10), (34, 197, 94)

# ======================================================================
# chair facts (from the built website data = the chair files)
# ======================================================================
def site_data():
    h = open(os.path.join(ROOT, 'Chair Website.html'), encoding='utf8').read()
    i = h.index('window.CHAIR_DATA = ') + 20
    return {c['id']: c for c in json.loads(h[i:h.index(';</script>', i)])['chairs']}

def strip_md(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&lt;', '<').replace('&gt;', '>')
    s = re.sub(r'\*\*|`', '', s)
    # the video fonts have no Japanese: drop Japanese words (and brackets around them) from on-screen text
    s = re.sub(r'\s*[(（][^()（）]*[\u3000-\u9fff\uff00-\uffef][^()（）]*[)）]', '', s)
    s = re.sub(r'[\u3000-\u9fff\uff00-\uffef]+', '', s)
    return re.sub(r'\s{2,}', ' ', s).strip()

def bullets(c, name):
    for s in c['sections']:
        if s['heading'].lower().startswith(name):
            return [strip_md(x) for x in re.findall(r'<li>(.*?)</li>', s['html'], re.S)]
    return []

def short(s, n=44):
    s = s.strip().rstrip('.')
    if len(s) <= n: return s
    for sep in [': ', '; ', ' (', ', ', ' — ', ' - ', ' at ', ' with ', ' plus ']:
        k = s.find(sep)
        if 12 <= k <= n: return s[:k]
    cut = s[:n].rsplit(' ', 1)[0]
    return cut + '…'

def peso(n): return '₱{:,.0f}'.format(n)

OB_RE = re.compile(r'[A-Z]{3,4}S[WN]A[A-Z]{3}\d{4}')

def facts(c):
    f, d = c['fields'], c['d']
    t = c['title']; k = t.find(': ')
    name = t if k < 0 else t[:k]
    name = strip_md(re.sub(r'\s*\([^)]*\)\s*$', '', name))  # drop "(C342GR)" from the spoken name
    year = None
    for src in [strip_md(c['introHtml'])] + bullets(c, 'at a glance') + bullets(c, 'cons'):
        y = re.search(r'(?:[Mm]ade (?:in )?|probably made |lot |\()(?:\d{1,2} \w+ )?(19[89]\d|20[0-2]\d)\b', src)
        if y: year = int(y.group(1)); break
    seat = d.get('seatMin'), d.get('seatMax')
    ob = OB_RE.search(json.dumps(c, ensure_ascii=False))
    return {
        'id': c['id'], 'name': name, 'brand': d['brand'] if d['brand'] != 'unknown' else 'Mystery',
        'price': d.get('price'), 'jp': d.get('jpPhp'), 'value': d.get('value'), 'pct': d.get('valuePct'),
        'seat': seat if seat[0] else None, 'slide': d.get('depthSlide'), 'arms': d.get('arms'), 'back': d.get('back'),
        'identified': d['identified'], 'year': year,
        'pros': [short(x) for x in bullets(c, 'pros')][:3] or ['Nobody wrote pros yet'],
        'cons': [short(x) for x in bullets(c, 'cons')][:3] or ['Nobody wrote cons yet'],
        'identify': strip_md((c.get('identify') or {}).get('first') or '') or None,
        'photos': [os.path.join(ROOT, p) for p in c.get('ownPhotos', [])],
        'priceNote': d.get('priceNote') or '',
        'ob': ob.group(0) if ob else None,
    }

def price_txt(F, ask='ask them 🤷'):
    if F['price'] is None: return ask
    return peso(F['price']) + (' (listing gone)' if 'removed' in F['priceNote'] else '')

def seat_txt(F):
    if not F['seat']: return None
    a, b = F['seat']
    return f'{a:g}–{b:g} cm'

# ======================================================================
# drawing toolkit
# ======================================================================
_fc = {}
def font(w, s, path=None):
    k = (w, s, path)
    if k not in _fc: _fc[k] = ImageFont.truetype(path or INTER % w, s)
    return _fc[k]

_ec = {}
def emoji(ch, size):
    if (ch, size) not in _ec:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new('RGBA', (200, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((100, 80), ch, font=f, embedded_color=True, anchor='mm')
        bb = im.getbbox() or (0, 0, 1, 1); im = im.crop(bb)
        r = size / max(im.size)
        _ec[(ch, size)] = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
    return _ec[(ch, size)]

EMO_RE = re.compile('([\U0001F000-\U0001FAFF☀-➿⭐↔-⇿‼⁉](?:️)?(?:‍[\U0001F000-\U0001FAFF☀-➿](?:️)?)*)')

def tlen(t, f):
    n = 0
    for part in EMO_RE.split(t):
        if not part: continue
        n += f.size * 1.15 if EMO_RE.fullmatch(part) else f.getlength(part)
    return n

def wrap(text, f, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w_ in para.split():
            t = (cur + ' ' + w_).strip()
            if tlen(t, f) <= maxw or not cur: cur = t
            else: lines.append(cur); cur = w_
        lines.append(cur)
    return lines

def draw_line(d, im, x, y, t, f, fill, stroke=0, stroke_fill=(0, 0, 0)):
    for part in EMO_RE.split(t):
        if not part: continue
        if EMO_RE.fullmatch(part):
            e = emoji(part, int(f.size * 1.05)); im.alpha_composite(e, (int(x), int(y + f.size * 0.1))); x += f.size * 1.15
        else:
            d.text((x, y), part, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill); x += f.getlength(part)

def label(text, f, fg=(255, 255, 255), bg=None, maxw=560, pad=(22, 12), r=18, stroke=0, align='center', lh=1.18):
    lines = wrap(text, f, maxw)
    a, dsc = f.getmetrics(); L = int((a + dsc) * lh)
    tw = max(tlen(l, f) for l in lines)
    im = Image.new('RGBA', (int(tw + 2 * pad[0] + 2 * stroke), int(L * len(lines) + 2 * pad[1] + 2 * stroke)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg: d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=bg)
    for i, l in enumerate(lines):
        x = (im.width - tlen(l, f)) / 2 if align == 'center' else pad[0]
        draw_line(d, im, x, pad[1] + i * L + stroke, l, f, fg, stroke)
    return im

def ease(t): t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def back_ease(t): t = max(0., min(1., t)); c = 1.9; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def paste(fr, im, x, y, alpha=1.0, scale=1.0, rot=0, anchor='c'):
    if alpha <= 0.01 or scale <= 0.01: return
    if scale != 1: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BILINEAR, expand=True)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    if anchor == 'c': x, y = x - im.width / 2, y - im.height / 2
    fr.alpha_composite(im, (int(x), int(y)))

def pop(fr, im, x, y, t, start, dur=0.35, out=None):
    """Bouncy pop-in at `start`, optional fade-out at `out`."""
    if t < start: return
    k = back_ease((t - start) / dur)
    a = min(1, (t - start) / 0.12)
    if out is not None and t > out: a *= max(0, 1 - (t - out) / 0.2)
    paste(fr, im, x, y, a, max(0.02, k))

def slide_in(fr, im, x, y, t, start, dur=0.4, dx=0, dy=40, out=None):
    if t < start: return
    k = ease((t - start) / dur); a = k
    if out is not None and t > out: a *= max(0, 1 - (t - out) / 0.2)
    paste(fr, im, x + dx * (1 - k), y + dy * (1 - k), a)

def load_photo(p):
    return ImageOps.exif_transpose(Image.open(p)).convert('RGB')

def cover(im, w, h, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    r = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.BILINEAR)
    x, y = int((r.width - w) * fx), int((r.height - h) * fy)
    return r.crop((x, y, x + w, y + h))

def contain_on_blur(im, w, h, dark=0.55):
    bg = cover(im, w, h).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * dark))
    s = min(w / im.width, h / im.height); fg = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2)); return bg

def kenburns(img, t, dur, z0=1.0, z1=1.12, dx=0.0, dy=0.0):
    k = 0.5 - 0.5 * math.cos(math.pi * min(1, t / dur))
    z = z0 + (z1 - z0) * k
    bw, bh = img.width / z, img.height / z
    cx = img.width / 2 + dx * k * img.width * 0.05; cy = img.height / 2 + dy * k * img.height * 0.05
    return img.resize((W, H), Image.BILINEAR, box=(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)).convert('RGBA')

def gradient(c1, c2, w=W, h=H, angle=0.0):
    y = np.linspace(0, 1, h)[:, None]; x = np.linspace(0, 1, w)[None, :]
    k = np.clip(y * math.cos(angle) + x * math.sin(angle), 0, 1)
    a = np.array(c1, float); b = np.array(c2, float)
    arr = a[None, None, :] * (1 - k[..., None]) + b[None, None, :] * k[..., None]
    return Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')

def mascot(color, size=520, mood='happy'):
    """A cute cartoon office chair, for chairs with no photo yet."""
    S = 4; im = Image.new('RGBA', (size * S, size * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    u = size * S / 100
    dark = tuple(int(c * 0.6) for c in color)
    d.rounded_rectangle([28 * u, 6 * u, 72 * u, 50 * u], 12 * u, fill=color, outline=dark, width=int(1.5 * u))
    d.rounded_rectangle([20 * u, 50 * u, 80 * u, 62 * u], 6 * u, fill=color, outline=dark, width=int(1.5 * u))
    d.rectangle([47 * u, 62 * u, 53 * u, 80 * u], fill=(90, 90, 100))
    for x2 in (14, 32, 50, 68, 86):
        d.line([(50 * u, 80 * u), (x2 * u, 88 * u)], fill=(70, 70, 80), width=int(3.5 * u))
        d.ellipse([(x2 - 3.5) * u, 87 * u, (x2 + 3.5) * u, 94 * u], fill=(40, 40, 48))
    ey = 24 * u
    for ex in (41, 59):
        d.ellipse([(ex - 4) * u, ey - 4.5 * u, (ex + 4) * u, ey + 4.5 * u], fill=(30, 30, 40))
        d.ellipse([(ex - 1.5) * u, ey - 3.5 * u, (ex + 1) * u, ey - 1 * u], fill=(255, 255, 255))
    if mood == 'happy': d.arc([43 * u, 27 * u, 57 * u, 39 * u], 20, 160, fill=(30, 30, 40), width=int(1.6 * u))
    else: d.arc([43 * u, 33 * u, 57 * u, 43 * u], 200, 340, fill=(30, 30, 40), width=int(1.6 * u))
    for bx in (35, 65): d.ellipse([(bx - 4) * u, 31 * u, (bx + 4) * u, 35 * u], fill=(255, 150, 170, 170))
    return im.resize((size, size), Image.LANCZOS)

def hero_image(F, w=W, h=H):
    """The chair's best photo filling the frame, or the cartoon chair on a soft background."""
    if F['photos']:
        im = load_photo(F['photos'][0])
        return (cover(im, w, h) if im.height / im.width > 1.2 else contain_on_blur(im, w, h)).convert('RGBA')
    col = BRAND_COL.get(F['brand'], (120, 120, 140))
    bg = gradient(tuple(min(255, c + 150) for c in col), tuple(min(255, c + 60) for c in col), w, h)
    m = mascot(col, int(min(w, h) * 0.8)); bg.alpha_composite(m, ((w - m.width) // 2, int(h * 0.5 - m.height * 0.38)))
    tag = label('🎨 cartoon · no photo yet', font('Bold', max(18, w // 26)), (40, 40, 50), (255, 255, 255, 220), w - 40, pad=(14, 6))
    bg.alpha_composite(tag, ((w - tag.width) // 2, int(h * 0.06)))
    return bg

def shade(fr, top=200, bottom=480, a=170):
    for hgt, at_top in ((top, True), (bottom, False)):
        if not hgt: continue
        g = np.linspace(a, 0, hgt) if at_top else np.linspace(0, a, hgt)
        m = Image.fromarray(np.repeat(g[:, None], W, 1).astype(np.uint8), 'L')
        blk = Image.new('RGBA', (W, hgt), (0, 0, 0, 255)); blk.putalpha(m)
        fr.alpha_composite(blk, (0, 0 if at_top else H - hgt))

def shake(t, amp=8, until=None):
    if until is not None and t > until: return 0, 0
    return int(amp * math.sin(t * 61)), int(amp * math.cos(t * 47))

def rounded(im, r=30):
    im = im.convert('RGBA'); mk = Image.new('L', im.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255); im.putalpha(mk); return im

CX = 340  # text centre: a little left, so the ChairTok buttons on the right never cover it

# ======================================================================
# formats: each returns (duration, draw(t) -> RGBA frame, music(seconds) -> samples)
# ======================================================================
JOKES = [
    ('Why did the chair go to therapy?', 'Too many issues with its back.'),
    ('Why don’t chairs win arguments?', 'They always take a seat.'),
    ('My chair and I have a lot in common.', 'We both recline under pressure.'),
    ('I told this chair a joke…', 'It didn’t get up. It just sat there.'),
    ('What’s a chair’s favourite music?', 'Anything with a good base.'),
    ('Is this chair single?', 'No. It’s in a sit-uationship.'),
]

def fmt_salesman(F, rnd):
    dur = 18.0
    hero = hero_image(F)
    burst = Image.new('RGBA', (1400, 1400), (0, 0, 0, 0)); bd = ImageDraw.Draw(burst)
    for k in range(24):
        bd.pieslice([0, 0, 1400, 1400], k * 15, k * 15 + 15, fill=(YEL if k % 2 else (255, 140, 0)) + (110,))
    T = lambda s, sz=58, bg=(255, 255, 255, 255), fg=(20, 20, 30): label(s, font('Black', sz), fg, bg, 600, pad=(22, 10))
    hook = T('😩 TIRED of chairs that are… just chairs?', 46)
    hot = T('🔥 HOT DEAL 🔥', 50, PINK + (255,), (255, 255, 255))
    jp = label(('New in Japan ' + peso(F['jp'])) if F['jp'] else 'Normal price: A LOT', font('Black', 46), (255, 255, 255), (0, 0, 0, 190), 600, pad=(22, 10))
    now = label('NOW ' + price_txt(F, 'ASK! 🤷'), font('Black', 84), (255, 255, 255), PINK + (255,), 640, pad=(26, 8))
    has = [T('✅ ' + p, 38, (255, 255, 255, 240)) for p in F['pros'][:3]]
    extra = T('💺 ' + (('Seat ' + seat_txt(F)) if seat_txt(F) else 'It is a chair. You sit on it.'), 38, (255, 255, 255, 240))
    wait = label('BUT WAIT!!', font('Black', 110), YEL, None, 700, pad=(0, 0), stroke=6)
    more = T('THERE’S MORE!!', 64, PINK + (255,), (255, 255, 255))
    fine = label('*fine print: ' + F['cons'][0].lower(), font('SemiBold', 30), (255, 255, 255), (0, 0, 0, 200), 600, pad=(16, 8))
    one = T('⚠️ Only ONE of this exact chair', 42, YEL + (255,))
    call = T('📞 MESSAGE OFFICE BUSTERS NOW!!!', 44, GRN + (255,), (255, 255, 255))
    jk = label('(we don’t get commission 😭)', font('Bold', 30), (255, 255, 255), (0, 0, 0, 170), 600, pad=(14, 6))
    def draw(t):
        fr = kenburns(hero, t, dur, 1.0, 1.18, 0.4, -0.3)
        shade(fr, 160, 420, 140)
        if 7.6 < t < 12.6:
            b = burst.rotate(t * 40, Image.BILINEAR); fr.alpha_composite(b, ((W - b.width) // 2, 640 - b.height // 2))
        sx, sy = shake(t, 10) if (3.4 < t < 4.0 or 7.6 < t < 8.3) else (0, 0)
        if t < 3.4:
            pop(fr, hot, CX, 230, t, 0.1); pop(fr, hook, CX, 420, t, 0.5)
        elif t < 7.6:
            pop(fr, jp, CX + sx, 360, t, 3.4)
            if t > 4.2:
                d = ImageDraw.Draw(fr); k = ease((t - 4.2) / 0.3)
                d.line([(CX - jp.width / 2, 362), (CX - jp.width / 2 + jp.width * k, 362)], fill=PINK, width=10)
            pop(fr, now, CX + sx, 520 + sy, t, 4.6, dur=0.45)
            for i, hh in enumerate(has[:2]): slide_in(fr, hh, CX, 680 + i * 90, t, 5.6 + 0.5 * i)
        elif t < 12.6:
            pop(fr, wait, CX + sx, 330 + sy, t, 7.6, dur=0.3)
            pop(fr, more, CX, 470, t, 8.3)
            for i, hh in enumerate(has[2:3] + [extra]): slide_in(fr, hh, CX, 600 + i * 90, t, 9.0 + 0.6 * i)
            slide_in(fr, fine, CX, 800, t, 10.6, dy=10)
        else:
            pop(fr, one, CX, 330, t, 12.6)
            pop(fr, call, CX + int(4 * math.sin(t * 30)), 470, t, 13.4)
            pop(fr, jk, CX, 580, t, 15.0)
        return fr
    def music(sec):
        m = beat_track(sec, 128, style='budots', key=0, seed=rnd)
        sfx_cash(m, 4.6); sfx_boom(m, 3.4); sfx_boom(m, 7.6); sfx_whoosh(m, 12.6); sfx_ding(m, 13.4)
        return m
    return dur, draw, music

def fmt_jokes(F, rnd):
    dur = 19.0
    hero = hero_image(F, 520, 640)
    r = random.Random(rnd); js = r.sample(JOKES, 2)
    wall = gradient((40, 18, 24), (12, 8, 12)); d0 = ImageDraw.Draw(wall)
    for y in range(0, H, 46):
        off = 0 if (y // 46) % 2 else 60
        for x in range(-off, W, 120): d0.rectangle([x + 3, y + 3, x + 117, y + 43], outline=(70, 30, 36), width=2)
    sp = Image.new('L', (W, H), 0); ImageDraw.Draw(sp).ellipse([40, 150, 680, 1050], fill=110)
    sp = sp.filter(ImageFilter.GaussianBlur(60)); spot = Image.new('RGBA', (W, H), (255, 240, 200, 255)); spot.putalpha(sp)
    wall.alpha_composite(spot)
    frame_card = Image.new('RGBA', (hero.width + 24, hero.height + 24), (255, 255, 255, 255)); frame_card.alpha_composite(hero, (12, 12))
    mic = emoji('🎤', 90); laugh = emoji('😂', 80)
    J = [(label(q, font('Black', 44), (255, 255, 255), (0, 0, 0, 200), 600), label(a, font('Black', 48), (20, 20, 30), YEL + (255,), 600)) for q, a in js]
    rimshot = label('ba dum tss 🥁', font('Black', 40), PINK, None, 600, stroke=3)
    real = [label('REAL TALK: ' + x, font('Bold', 36), (255, 255, 255), (30, 90, 200, 235), 600)
            for x in [F['name'] + ' · ' + price_txt(F, 'price: ask the shop'),
                      ('Seat ' + seat_txt(F)) if seat_txt(F) else F['pros'][0], 'Downside: ' + F['cons'][0].lower()]]
    end = label('I’ll be here all week. 🙇', font('Black', 42), (255, 255, 255), PINK + (255,), 600)
    def draw(t):
        fr = wall.copy()
        paste(fr, frame_card, CX, 700, 1, 0.92 + 0.02 * math.sin(t * 2), 3 * math.sin(t * 1.3))
        paste(fr, mic, 600, 1060, 1)
        if 0.3 <= t < 4.6 or 7.8 <= t < 12.4:
            a = 0.3 if t < 4.6 else 7.8; q, ans = J[0 if t < 4.6 else 1]
            slide_in(fr, q, CX, 200, t, a); pop(fr, ans, CX, 330, t, a + 2.0); pop(fr, rimshot, CX, 440, t, a + 2.6)
            if t > a + 2.6: paste(fr, laugh, 110 + 10 * math.sin(t * 20), 440, 1)
        elif 4.8 <= t < 7.6:
            slide_in(fr, real[0], CX, 210, t, 4.8); slide_in(fr, real[1], CX, 320, t, 5.4)
        elif t >= 12.6:
            slide_in(fr, real[2], CX, 210, t, 12.6); pop(fr, end, CX, 340, t, 14.0)
        return fr
    def music(sec):
        m = beat_track(sec, 96, style='jazz', key=5, seed=rnd, vol=0.6)
        sfx_rimshot(m, 2.9); sfx_rimshot(m, 10.4); sfx_wahwah(m, 13.0)
        return m
    return dur, draw, music

def fmt_aislop(F, rnd):
    dur = 19.0
    bg = gradient((120, 90, 255), (255, 160, 220), angle=0.6)
    card = rounded(hero_image(F, 520, 620), 40)
    glass = lambda s, sz=36, w='SemiBold': label(s, font(w, sz), (40, 30, 80), (255, 255, 255, 195), 560, pad=(24, 16), r=24)
    title = label('✨ Unlocking Seating Excellence: The ' + F['name'] + ' Journey 🚀', font('ExtraBold', 44), (255, 255, 255), None, 600)
    intro = glass('In today’s fast-paced world, a chair is more than a chair. It’s a lifestyle. 🌍✨')
    delve = glass('Let’s delve into the key takeaways: 🧵👇', 40, 'Bold')
    pts = F['pros'][:2] + [('Seat height: ' + seat_txt(F)) if seat_txt(F) else F['pros'][-1]]
    keys = [glass(e + ' ' + x, 34) for e, x in zip(['💡', '🎯', '🌱'], pts)]
    but = glass('⚠️ However, it’s important to note: ' + F['cons'][0].lower() + '.', 32)
    concl = glass('In conclusion, this chair is a testament to the transformative power of chairs. 🌟', 34)
    cta = label('👍 Like · 🔁 Share · 🔔 Synergy', font('Bold', 32), (255, 255, 255), (90, 60, 220, 230), 600)
    wm = label('Generated with AI ✨ · may contain extra fingers', font('SemiBold', 22), (255, 255, 255), (0, 0, 0, 90), 600, pad=(12, 6))
    spark = [emoji(e, 40) for e in ['✨', '🌟', '💫']]
    rr = random.Random(rnd); sp = [(rr.uniform(0, W), rr.uniform(0, H), rr.uniform(0.5, 2), rr.randrange(3)) for _ in range(18)]
    def draw(t):
        fr = bg.copy()
        fr.alpha_composite(Image.new('RGBA', (W, H), (int(127 + 127 * math.sin(t * 0.7)), 120, 255, 50)))
        for x, y, s, k in sp: paste(fr, spark[k], x, (y - t * 40 * s) % H, 0.5 + 0.5 * math.sin(t * 3 * s), 0.6 + 0.3 * math.sin(t * s))
        if t < 3.6:
            paste(fr, card, CX, 760, ease(t / 0.8), 0.9 + 0.05 * t / 3.6); slide_in(fr, title, CX, 280, t, 0.2)
        elif t < 7.0:
            paste(fr, card, CX, 820, 1, 0.75); slide_in(fr, intro, CX, 300, t, 3.6)
        elif t < 13.0:
            slide_in(fr, delve, CX, 220, t, 7.0)
            for i, k_ in enumerate(keys): slide_in(fr, k_, CX, 390 + i * 165, t, 7.8 + 1.4 * i, dx=-80, dy=0)
        elif t < 16.0:
            paste(fr, card, CX, 820, 1, 0.75); slide_in(fr, but, CX, 300, t, 13.0)
        else:
            slide_in(fr, concl, CX, 330, t, 16.0); pop(fr, cta, CX, 560, t, 17.0)
        paste(fr, wm, CX, 1000, 0.9)
        return fr
    def music(sec):
        m = beat_track(sec, 90, style='corporate', key=2, seed=rnd, vol=0.8)
        for a in (3.6, 7.0, 13.0, 16.0): sfx_whoosh(m, a)
        for a in (7.8, 9.2, 10.6): sfx_ding(m, a, 1568)
        return m
    return dur, draw, music

def fmt_spin(F, rnd):
    dur = 17.0
    cards = [rounded(cover(load_photo(p), 460, 620), 30) for p in F['photos']] or [rounded(hero_image(F, 460, 620), 30)]
    bg = gradient((10, 14, 30), (40, 10, 60))
    badge = label('360° VIEW 🔄', font('Black', 50), (10, 10, 20), CYAN + (255,), 600)
    n = len(F['photos'])
    joke = label(f'(we have {n or "zero"} photo{"" if n == 1 else "s"}. it’s fine. 🙂)', font('Bold', 30), (255, 255, 255), (0, 0, 0, 150), 600, pad=(14, 6))
    specs = [x for x in [('Seat ' + seat_txt(F)) if seat_txt(F) else None,
                         {'yes': 'Seat slides ↔️', 'no': 'No seat slide'}.get(F['slide']),
                         {'mesh': 'Mesh back 🌬️', 'fabric': 'Fabric back 🧵'}.get(F['back']),
                         {'yes': 'Has arms 💪', 'no': 'No arms', 'both': 'Arms optional'}.get(F['arms']),
                         'Price ' + price_txt(F, 'ask')] if x]
    tags = [label(s, font('Bold', 32), (255, 255, 255), (255, 255, 255, 45), 400, pad=(16, 8), r=20) for s in specs]
    nm = label(F['name'], font('Black', 50), (255, 255, 255), None, 640)
    def draw(t):
        fr = bg.copy(); d = ImageDraw.Draw(fr)
        for k in range(6):
            rr_ = 160 + k * 40 + (t * 30) % 40
            d.ellipse([CX - rr_ * 1.6, 1010 - rr_ * 0.3, CX + rr_ * 1.6, 1010 + rr_ * 0.3], outline=(80, 200, 255, max(0, 120 - k * 20)), width=2)
        ang = t * 2 * math.pi / 3.2
        c = math.cos(ang); i = int((ang + math.pi / 2) // math.pi) % len(cards)
        card = cards[i]; wpx = max(2, int(card.width * abs(c)))
        sq = card.resize((wpx, card.height), Image.BILINEAR)
        if c < 0:
            a_ = sq.getchannel('A'); sq = ImageOps.mirror(sq).convert('RGB'); sq = Image.blend(sq, Image.new('RGB', sq.size, (0, 0, 0)), 0.35).convert('RGBA'); sq.putalpha(ImageOps.mirror(a_))
        sh = Image.new('RGBA', (int(wpx * 1.1) + 20, 60), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([0, 0, sh.width - 1, 59], fill=(0, 0, 0, 140))
        paste(fr, sh.filter(ImageFilter.GaussianBlur(10)), CX, 1000, 1)
        paste(fr, sq, CX, 660 + 10 * math.sin(t * 2), 1)
        pop(fr, badge, CX, 210, t, 0.2); pop(fr, nm, CX, 300, t, 0.6)
        for k, tg in enumerate(tags):
            st = 2.0 + k * 2.2; last = k == len(tags) - 1
            if st <= t < st + (99 if last else 2.2):
                side = -1 if k % 2 == 0 else 1
                slide_in(fr, tg, CX + side * 120, 400 + (k % 2) * 60, t, st, dx=side * 220, dy=0, out=None if last else st + 2.0)
        if t > 13.5: pop(fr, joke, CX, 1090, t, 13.5)
        return fr
    def music(sec):
        m = beat_track(sec, 124, style='techno', key=9, seed=rnd)
        for k in range(len(tags)): sfx_whoosh(m, 2.0 + k * 2.2, 0.25)
        return m
    return dur, draw, music

def fmt_documentary(F, rnd):
    dur = 20.0
    hero = hero_image(F)
    ep = random.Random(rnd).randint(2, 9)
    serif = font('I', 36, SERIF_I)
    lines = [
        f'Here, in the wild aisles of Office Busters, we observe the {F["name"]}.',
        (f'Born in Japan around {F["year"]}, it has survived {2026 - F["year"]} years of office life.' if F['year'] else 'Its age remains one of nature’s great mysteries.'),
        f'Observe its greatest strength: {F["pros"][0].lower()}.',
        f'But nature is cruel. {F["cons"][0]}.',
        'It waits patiently for a human to sit. Nature is beautiful.',
    ]
    subs = [label(l, serif, (255, 255, 210), (0, 0, 0, 150), 600, pad=(18, 10), r=8) for l in lines]
    tcard = label(f'EPISODE {ep}', font('B', 30, SERIF_B), (230, 220, 180), None, 600)
    tname = label(F['name'], font('B', 56, SERIF_B), (255, 255, 255), None, 640)
    bars = 130
    def draw(t):
        fr = kenburns(hero, t, dur, 1.05, 1.28, -0.6, 0.4)
        fr.alpha_composite(Image.new('RGBA', (W, H), (255, 190, 120, 28)))
        d = ImageDraw.Draw(fr); d.rectangle([0, 0, W, bars], fill=(0, 0, 0)); d.rectangle([0, H - bars, W, H], fill=(0, 0, 0))
        if t < 3.2:
            a = min(1, t / 0.8) * (1 if t < 2.6 else max(0, 1 - (t - 2.6) / 0.6))
            fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(150 * a))))
            paste(fr, tcard, CX, 520, a); paste(fr, tname, CX, 610, a)
        else:
            k = min(int((t - 3.2) // 3.36), len(subs) - 1); st = 3.2 + k * 3.36
            a = min(1, (t - st) / 0.5) * (1 if (t < st + 3.0 or k == len(subs) - 1) else max(0, 1 - (t - st - 3.0) / 0.36))
            paste(fr, subs[k], CX, 880, a)
        return fr
    def music(sec): return beat_track(sec, 70, style='strings', key=7, seed=rnd, vol=0.75)
    return dur, draw, music

def fmt_mystery(F, rnd):
    dur = 19.0
    hero = hero_image(F, 560, 760)
    sil = hero.convert('L').point(lambda v: 10 if v < 140 else 40).convert('RGB')
    sil = Image.blend(sil, Image.new('RGB', sil.size, (20, 30, 120)), 0.55)
    hero = rounded(hero, 30); sil = rounded(sil, 30)
    rays = Image.new('RGBA', (1600, 1600), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
    for k in range(20): rd.pieslice([0, 0, 1600, 1600], k * 18, k * 18 + 9, fill=(255, 220, 60, 90))
    title = label('WHO’S THAT CHAIR?!', font('Black', 70), YEL, None, 700, stroke=6)
    qm = emoji('❓', 170)
    brand = F['brand'] if F['brand'] != 'Mystery' else None
    rev = label((f'It’s… a {brand}! 🎉' if brand else 'It’s… a chair! 🎉'), font('Black', 60), (255, 255, 255), PINK + (255,), 640)
    which = label('…but WHICH model?! 🤔 Nobody knows yet.', font('Black', 42), (20, 20, 30), (255, 255, 255, 245), 600)
    help_ = label('🕵️ HELP SOLVE THE CASE:', font('Black', 44), (255, 255, 255), (30, 90, 200, 255), 600)
    step = label(F['identify'] or 'Ask for one photo of the whole underside of the seat', font('Bold', 34), (20, 20, 30), YEL + (255,), 580)
    clue = label(('🔎 Clue: sticker ' + F['ob']) if F['ob'] else '🔎 Clue: check under the seat', font('Bold', 32), (255, 255, 255), (0, 0, 0, 190), 600)
    tip = label('📸 Tip: one photo of the WHOLE underside shows every label', font('SemiBold', 32), (255, 255, 255), (0, 0, 0, 170), 600)
    pr = label('Price: ' + price_txt(F, 'also a mystery 💀'), font('Black', 44), (255, 255, 255), PINK + (255,), 600)
    def draw(t):
        fr = gradient((20, 60, 200), (90, 20, 160))
        r_ = rays.rotate(t * 25, Image.BILINEAR); fr.alpha_composite(r_, ((W - 1600) // 2, 640 - 800))
        pop(fr, title, CX, 190, t, 0.1)
        if t < 5.0:
            sx, sy = shake(t, 4)
            paste(fr, sil, CX + sx, 660 + sy, 1, 0.9 + 0.03 * math.sin(t * 8)); pop(fr, qm, CX, 660, t, 0.6)
        else:
            paste(fr, hero, CX, 690, 1, 0.75 if t > 8.6 else 0.9)
            if t < 5.5: fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * (1 - ease((t - 5.0) / 0.5))))))
            if t < 8.6:
                pop(fr, rev, CX, 330, t, 5.2); pop(fr, which, CX, 1070, t, 6.6)
            else:
                fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 130)))
                if t < 14.2:
                    pop(fr, help_, CX, 330, t, 8.6); slide_in(fr, step, CX, 520, t, 9.2); slide_in(fr, clue, CX, 760, t, 10.6)
                else:
                    pop(fr, tip, CX, 420, t, 14.2); pop(fr, pr, CX, 600, t, 15.2)
        return fr
    def music(sec):
        m = beat_track(sec, 110, style='gameshow', key=3, seed=rnd, vol=0.6, start=5.0)
        sfx_drumroll(m, 0.3, 4.6); sfx_sting(m, 5.0); sfx_ding(m, 8.6)
        return m
    return dur, draw, music

def fmt_dating(F, rnd):
    dur = 18.0
    photo = hero_image(F, 600, 760)
    age = (2026 - F['year']) if F['year'] else None
    nm = F['name'] if len(F['name']) <= 16 else F['name'].split()[-1]
    head = label(f'{nm}, {age if age else "age: secret 🤫"}', font('Black', 44), (255, 255, 255), None, 540, align='left', pad=(0, 0))
    sub = label('📍 Office Busters PH · 0 km away', font('SemiBold', 28), (255, 255, 255), None, 560, align='left', pad=(0, 0))
    cw = photo.copy()
    g = np.linspace(0, 210, 300); blk = Image.new('RGBA', (cw.width, 300), (0, 0, 0, 255))
    blk.putalpha(Image.fromarray(np.repeat(g[:, None], cw.width, 1).astype(np.uint8), 'L'))
    cw.alpha_composite(blk, (0, cw.height - 300))
    cw.alpha_composite(sub, (28, cw.height - 30 - sub.height)); cw.alpha_composite(head, (28, cw.height - 40 - sub.height - head.height))
    cw = rounded(cw, 34)
    bio = [('💬 Bio', 'Looking for someone who sits a lot. Will support you (lower back included).'),
           ('💚 Green flags', ' · '.join(F['pros'][:2])),
           ('🚩 Red flags', ' · '.join(F['cons'][:2])),
           ('💸 First date costs', price_txt(F, 'ask me 😉'))]
    cards = [label(h + '\n' + b, font('Bold', 32), (30, 30, 40), (255, 255, 255, 245), 560, pad=(24, 16), r=22) for h, b in bio]
    match = label('IT’S A MATCH! 💘', font('Black', 76), (255, 255, 255), None, 700, stroke=5)
    heart = emoji('💖', 120); nope = emoji('❌', 90); yes = emoji('💚', 90)
    nxt = label('swipe up to meet the next one 👆', font('Bold', 32), (255, 255, 255), (0, 0, 0, 120), 600)
    bgc = gradient((255, 88, 120), (255, 160, 90), angle=0.4)
    def draw(t):
        fr = bgc.copy()
        if t < 12.6:
            paste(fr, cw, CX, 560, 1)
            if t >= 3.0:
                k = min(int((t - 3.0) // 2.4), 3); st = 3.0 + k * 2.4
                slide_in(fr, cards[k], CX, 870, t, st, dy=60, out=st + 2.2 if k < 3 else None)
            pop(fr, nope, 170, 1090, t, 0.6); pop(fr, yes, 510, 1090, t, 0.8)
        else:
            k = ease((t - 12.6) / 0.6)
            paste(fr, cw, CX + 700 * k, 560 - 80 * k, 1 - k * 0.6, 1, -25 * k)
            pop(fr, match, CX, 520, t, 13.1)
            if t > 13.0:
                for i in range(10): paste(fr, heart, (i * 77 + 40) % W, 1300 - ((t - 13.0) * 300 + i * 120) % 1400, 0.9, 0.4 + 0.1 * (i % 3))
            pop(fr, nxt, CX, 700, t, 14.6)
        return fr
    def music(sec):
        m = beat_track(sec, 84, style='lofi', key=4, seed=rnd, vol=0.8)
        sfx_whoosh(m, 12.6); sfx_ding(m, 13.1, 1318); sfx_ding(m, 13.25, 1760)
        return m
    return dur, draw, music

def fmt_news(F, rnd):
    dur = 17.0
    photo = hero_image(F, 600, 440)
    ImageDraw.Draw(photo).rectangle([0, 0, photo.width - 1, photo.height - 1], outline=(255, 255, 255), width=6)
    head = f'CHAIR SPOTTED AT OFFICE BUSTERS FOR {price_txt(F, "AN UNKNOWN PRICE").upper()}'
    tick = '   •   '.join([F['name'].upper()] + [p.upper() for p in F['pros']] + ['WARNING: ' + c.upper() for c in F['cons'][:2]] + ['IN OTHER NEWS: ' + random.Random(rnd).choice(FACTS)[0].upper(), 'MORE AT 11']) + '   •   '
    tick_img = label(tick * 2, font('Bold', 30), (255, 255, 255), None, 99999, pad=(0, 0))
    lines = [('EXPERTS SAY', F['pros'][0]), ('CRITICS WARN', F['cons'][0]), ('SEAT HEIGHT', seat_txt(F) or 'classified 🤐')]
    boxes = [label(a + ':\n' + b, font('Black', 40), (255, 255, 255), (16, 32, 80, 240), 600, pad=(24, 14), r=10) for a, b in lines]
    breaking = label('BREAKING NEWS', font('Black', 64), (255, 255, 255), (210, 20, 30, 255), 700, pad=(28, 10), r=6)
    hl = label(head, font('Black', 40), (20, 20, 30), (255, 255, 255, 255), 620, pad=(22, 12), r=6)
    live = label('● LIVE', font('Black', 28), (255, 255, 255), (210, 20, 30, 255), 200, pad=(14, 6), r=6)
    base = gradient((10, 20, 60), (30, 50, 120))
    def draw(t):
        fr = base.copy(); d = ImageDraw.Draw(fr)
        for k in range(12): d.line([(0, 140 + k * 100 + (t * 40) % 100), (W, 100 + k * 100 + (t * 40) % 100)], fill=(60, 90, 170), width=2)
        sx, _ = shake(t, 6, 0.8)
        pop(fr, breaking, CX + sx, 190, t, 0.0, dur=0.25)
        paste(fr, photo, CX, 520, ease(t / 0.6))
        if int(t * 2) % 2 == 0: paste(fr, live, CX - 220, 335, 1)
        if t < 4.5: slide_in(fr, hl, CX, 830, t, 0.8, dx=-600, dy=0)
        else:
            k = min(2, int((t - 4.5) // 3.5)); slide_in(fr, boxes[k], CX, 830, t, 4.5 + k * 3.5, dx=600, dy=0)
        d.rectangle([0, 1000, W, 1050], fill=(210, 20, 30))
        off = int((t * 160) % (tick_img.width / 2))
        fr.alpha_composite(tick_img.crop((off, 0, off + W, tick_img.height)), (0, 1006))
        return fr
    def music(sec):
        m = beat_track(sec, 120, style='news', key=10, seed=rnd, vol=0.8)
        sfx_boom(m, 0.0)
        for a in (4.5, 8.0, 11.5): sfx_whoosh(m, a, 0.25)
        return m
    return dur, draw, music

def fmt_pov(F, rnd):
    dur = 17.0
    hero = hero_image(F)
    meme = lambda s, sz=56: label(s, font('Black', sz), (255, 255, 255), None, 620, pad=(6, 4), stroke=5)
    seat = F['seat']
    if seat:
        diff = seat[0] - POPLITEAL
        verdict = (f'your feet touch the floor 😭✨ (lowest seat {seat[0]:g} cm)') if diff <= 0 else (f'your feet: 🦶 … floor? 🫥 (+{diff:.1f} cm too high, get a footrest)')
    else:
        verdict = 'seat height: nobody knows 💀 (bring a tape measure)'
    segs = [(0, 3.0, meme(f'POV: you’re 150 cm and you just found the {F["name"]}', 48)),
            (3.0, 5.6, meme('the price: ' + price_txt(F, '¯\\_(ツ)_/¯ ask them'), 50)),
            (5.6, 8.6, meme(verdict, 44)),
            (8.6, 11.4, meme('the good part: ' + F['pros'][0].lower(), 44)),
            (11.4, 14.2, meme('the catch: ' + F['cons'][0].lower(), 44)),
            (14.2, 17.0, meme('me adding it to the chair library anyway 🧘', 46))]
    feet = emoji('🦶', 90)
    def draw(t):
        fr = kenburns(hero, t, dur, 1.0, 1.15, 0, 0.3)
        if (t * 128 / 60) % 2 < 0.15 and t > 2:   # zoom punch on the beat
            z = fr.resize((int(W * 1.05), int(H * 1.05)), Image.BILINEAR)
            fr = z.crop(((z.width - W) // 2, (z.height - H) // 2, (z.width - W) // 2 + W, (z.height - H) // 2 + H))
        shade(fr, 440, 300, 170)
        for a, b, im in segs:
            if a <= t < b: pop(fr, im, CX, 300, t, a + 0.05, dur=0.25)
        if 5.6 <= t < 8.6 and seat and seat[0] > POPLITEAL:
            paste(fr, feet, 220 + 30 * math.sin(t * 9), 900 + 20 * abs(math.sin(t * 9)), 1, 1, 20 * math.sin(t * 9))
            paste(fr, feet, 460 + 30 * math.sin(t * 9 + 1), 900 + 20 * abs(math.sin(t * 9 + 1)), 1, 1, -20 * math.sin(t * 9))
        return fr
    def music(sec):
        m = beat_track(sec, 128, style='budots', key=7, seed=rnd)
        for a in (3.0, 5.6, 8.6, 11.4, 14.2): sfx_whoosh(m, a, 0.2)
        return m
    return dur, draw, music


# random non-chair things (all true facts)
FACTS = [
    ('Octopuses have three hearts', '🐙'),
    ('A group of flamingos is called a flamboyance', '🦩'),
    ('Bananas are berries. Strawberries are not.', '🍌'),
    ('Honey never spoils', '🍯'),
    ('Sloths can hold their breath longer than dolphins', '🦥'),
    ('Wombat poop is cube-shaped', '🟫'),
    ('A day on Venus is longer than its year', '🪐'),
]
CAMEOS = [('🦆', 'a duck. no reason.'), ('🥔', 'a potato. that’s it.'), ('🐸', 'frog break 🐸'), ('🍞', 'bread. just bread.'), ('🐈', 'cat tax 🐈')]

def runner_frame(t, w=W, h=H // 2, seed=0):
    """Original endless-runner 'gameplay' for the bottom half (brain rot split screen)."""
    im = gradient((90, 170, 255), (190, 230, 255), w, h); d = ImageDraw.Draw(im)
    hz_y = int(h * 0.28)
    d.rectangle([0, hz_y, w, h], fill=(70, 70, 82))
    vx = w / 2
    for k in (-1.5, -0.5, 0.5, 1.5):  # lane lines
        d.line([(vx + k * 18, hz_y), (vx + k * 300, h)], fill=(230, 230, 240), width=4)
    for k in range(14):  # moving stripes
        z = ((k / 14) + t * 1.2) % 1; y = hz_y + (h - hz_y) * z ** 2
        d.rectangle([0, y, 40, y + 6 + 20 * z], fill=(255, 200, 0)); d.rectangle([w - 40, y, w, y + 6 + 20 * z], fill=(255, 200, 0))
    r = random.Random(seed)
    for k in range(6):  # coins and boxes coming at you
        z = ((k / 6) + t * 0.9 + r.random()) % 1; lane = (k * 7 + seed) % 3 - 1
        y = hz_y + (h - hz_y) * z ** 2; x = vx + lane * (40 + 260 * z ** 2); s = 8 + 60 * z ** 2
        if k % 2: d.ellipse([x - s / 2, y - s, x + s / 2, y], fill=(255, 215, 0), outline=(200, 150, 0), width=3)
        else: d.rectangle([x - s * 0.7, y - s * 1.2, x + s * 0.7, y], fill=(170, 110, 60), outline=(110, 70, 30), width=3)
    lane = [-1, 0, 1, 0][int(t / 1.1) % 4]; px = vx + lane * 220; py = h - 70 - abs(math.sin(t * 9)) * 26
    d.ellipse([px - 34, py - 120, px + 34, py - 52], fill=(255, 120, 60))                  # runner: head
    d.rounded_rectangle([px - 30, py - 56, px + 30, py + 10], 14, fill=(40, 200, 140))     # body
    sw = math.sin(t * 18) * 22
    d.line([(px - 12, py + 8), (px - 12 + sw, py + 52)], fill=(30, 30, 40), width=12)
    d.line([(px + 12, py + 8), (px + 12 - sw, py + 52)], fill=(30, 30, 40), width=12)
    sc = label(f'🪙 {int(t * 37) * 10}', font('Black', 30), (255, 255, 255), (0, 0, 0, 120), 300, pad=(12, 4))
    im.alpha_composite(sc, (w - sc.width - 20, 16))
    return im

def word_captions(lines, t0, per=0.30):
    """TikTok auto-captions: 1-3 words at a time, the newest word yellow."""
    out = []; t = t0
    for line in lines:
        words = line.split(); chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
        for ch in chunks:
            for j in range(len(ch)): out.append((t, ch, j)); t += per
        t += 0.25
    return out, t

def fmt_brainrot(F, rnd):
    dur = 19.0
    top = hero_image(F, W, H // 2)
    r = random.Random(rnd)
    fact, femo = r.choice(FACTS); cam, camtxt = r.choice(CAMEOS)
    seat = seat_txt(F)
    script = [f'bro this {F["name"]} got RIZZ 💀',
              f'{price_txt(F, "price unknown")} ?? no cap fr fr',
              (f'seat {seat} sigma posture unlocked 🗿' if seat else 'seat height? nobody knows 🗿'),
              'POV: ' + F['pros'][0].lower() + ' 🔥']
    script2 = ['ok but ' + F['cons'][0].lower() + ' 😭', 'still bussin tho', 'follow for part 2 🙏']
    caps, t_mid = word_captions(script, 0.4)
    INT = (t_mid, t_mid + 2.6)                      # random interruption
    caps2, _ = word_captions(script2, INT[1] + 0.2)
    caps += caps2
    cf = font('Black', 64)
    boom_words = [c[0] for c in caps if any(x in ' '.join(c[1]) for x in ('💀', 'RIZZ', '🗿', '😭'))]
    fact_card = label(f'random fact: {fact} {femo}', font('Black', 50), (20, 20, 30), YEL + (255,), 600, pad=(26, 16))
    cam_e = emoji(cam, 240); cam_l = label(camtxt, font('Black', 54), (255, 255, 255), None, 640, stroke=5)
    moai = emoji('🗿', 260)
    def draw(t):
        fr = Image.new('RGBA', (W, H))
        if INT[0] <= t < INT[1]:  # full-screen random cut
            k = t - INT[0]
            fr = gradient((255, 120, 200), (120, 200, 255), angle=t)
            paste(fr, cam_e, -150 + (W + 300) * (k / 2.6), 520 + 40 * math.sin(k * 8), 1, 1, 15 * math.sin(k * 10))
            pop(fr, cam_l, CX, 300, t, INT[0] + 0.1)
            pop(fr, fact_card, CX, 820, t, INT[0] + 0.9)
            return fr
        tf = kenburns(top.resize((W, H)), t, dur, 1.0, 1.1)  # simple zoom on the top half
        tf = tf.resize((W, H // 2))
        if any(0 <= t - b < 0.18 for b in boom_words):  # meme zoom punch
            tf = tf.resize((int(W * 1.12), int(H // 2 * 1.12))).crop((int(W * 0.06), int(H * 0.03), int(W * 0.06) + W, int(H * 0.03) + H // 2))
            tf = Image.blend(tf.convert('RGB'), Image.new('RGB', tf.size, (255, 255, 255)), 0.15).convert('RGBA')
        fr.alpha_composite(tf, (0, 0)); fr.alpha_composite(runner_frame(t, seed=rnd), (0, H // 2))
        cur = None
        for c in caps:
            if c[0] <= t: cur = c
        if cur and t - cur[0] < 0.9:
            ts, ch, j = cur
            words_im = []
            for k_, wd in enumerate(ch[:j + 1]):
                words_im.append(label(wd.upper(), cf, YEL if k_ == j else (255, 255, 255), None, 700, pad=(4, 0), stroke=6))
            tw = sum(w_.width for w_ in words_im) + 10 * (len(words_im) - 1)
            x = CX - tw / 2; sc = 0.85 + 0.15 * back_ease((t - ts) / 0.15)
            for w_ in words_im:
                paste(fr, w_, x + w_.width / 2, H // 2, 1, sc); x += w_.width + 10
        if any(0 <= t - b < 0.6 for b in boom_words if '🗿' in ' '.join(next(c[1] for c in caps if c[0] == b))):
            paste(fr, moai, CX, 300, 0.9)
        return fr
    def music(sec):
        m = beat_track(sec, 140, style='budots', key=r.randrange(12), seed=rnd)
        for b in boom_words: sfx_boom(m, b)
        sfx_whoosh(m, INT[0]); sfx_ding(m, INT[0] + 0.9, 1760)
        return m
    return dur, draw, music

def sidekick(t, mood=0.0):
    """An original nervous young salesperson (cartoon): teal hoodie, messy dark hair, big worried eyes."""
    S = 2; w, h = 420 * S, 620 * S; im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    jx = 3 * S * math.sin(t * 37); jy = 2 * S * math.cos(t * 29)       # nervous jitter
    cx, cy = w / 2 + jx, 230 * S + jy
    d.rounded_rectangle([cx - 150 * S, cy + 150 * S, cx + 150 * S, h], 70 * S, fill=(20, 150, 160))   # hoodie
    d.polygon([(cx - 40 * S, cy + 150 * S), (cx, cy + 210 * S), (cx + 40 * S, cy + 150 * S)], fill=(14, 110, 120))
    d.rectangle([cx - 30 * S, cy + 110 * S, cx + 30 * S, cy + 160 * S], fill=(250, 210, 180))       # neck
    d.ellipse([cx - 130 * S, cy - 130 * S, cx + 130 * S, cy + 140 * S], fill=(252, 214, 186))       # head
    for k in range(9):                                                                               # messy hair
        a = math.pi * (1.05 + k * 0.11); x0 = cx + 130 * S * math.cos(a); y0 = cy - 20 * S + 130 * S * math.sin(a)
        d.polygon([(x0 - 40 * S, y0 + 30 * S), (x0 + 10 * S * math.cos(a) * 3, y0 - 55 * S), (x0 + 40 * S, y0 + 30 * S)], fill=(40, 30, 40))
    d.ellipse([cx - 135 * S, cy - 150 * S, cx + 135 * S, cy - 40 * S], fill=(40, 30, 40))
    for ex in (-55, 55):                                                                              # big worried eyes
        d.ellipse([cx + (ex - 40) * S, cy - 35 * S, cx + (ex + 40) * S, cy + 45 * S], fill=(255, 255, 255), outline=(40, 30, 40), width=3 * S)
        px = cx + (ex + 6 * math.sin(t * 5)) * S; py = cy + 8 * S + 4 * S * math.sin(t * 7)
        d.ellipse([px - 9 * S, py - 9 * S, px + 9 * S, py + 9 * S], fill=(30, 30, 40))
        d.line([(cx + (ex - 38) * S, cy - 58 * S - (8 * S if ex < 0 else 0)), (cx + (ex + 38) * S, cy - 50 * S + (0 if ex < 0 else -8 * S))], fill=(40, 30, 40), width=6 * S)
    mw = 50 * S; my = cy + 85 * S                                                                     # wobbly mouth
    pts = [(cx - mw + k * mw / 6, my + 8 * S * math.sin(k * 1.7 + t * 14)) for k in range(13)]
    d.line(pts, fill=(120, 40, 50), width=6 * S)
    im = im.resize((w // S, h // S), Image.LANCZOS)
    sweat = emoji('💦', 54); im.alpha_composite(sweat, (300, int(60 + (t * 120) % 80)))
    return im

def fmt_nervous(F, rnd):
    dur = 19.0
    photo = rounded(hero_image(F, 400, 520), 26)
    lines = [
        ('U-um, h-hi! S-so this is the… ' + F['name'] + '…', 0.3),
        ('My b-boss said I have to s-sell it or I’m f-fired 😰', 3.4),
        ('It’s ' + price_txt(F, 'uh… I f-forgot the price 😅') + '! Th-that’s good, r-right?', 6.4),
        ('It has… ' + F['pros'][0].lower() + '! Y-yeah!', 9.2),
        ('P-please don’t look at the… ' + F['cons'][0].lower() + ' 😬', 12.0),
        ('P-please buy it. I have a f-family. (I’m a cartoon.) 🙏', 15.0),
    ]
    bubbles = [(label(txt, font('Bold', 36), (20, 20, 30), (255, 255, 255, 250), 540, pad=(24, 16), r=26), st) for txt, st in lines]
    bg = gradient((255, 236, 180), (255, 190, 150))
    def draw(t):
        fr = bg.copy(); d = ImageDraw.Draw(fr)
        for k in range(8): d.line([(k * 110 + (t * 20) % 110, 0), (k * 110 - 300 + (t * 20) % 110, H)], fill=(255, 215, 160), width=30)
        paste(fr, photo, 470, 760, 1, 1, 4 * math.sin(t * 2))
        tag = label('THE CHAIR →', font('Black', 26), (255, 255, 255), PINK + (255,), 300, pad=(12, 6)); paste(fr, tag, 470, 480, 1)
        paste(fr, sidekick(t), 200, 900, 1, 0.95)
        cur = [b for b in bubbles if b[1] <= t]
        if cur:
            im, st = cur[-1]
            sx = int(3 * math.sin(t * 50)) if t - st < 0.4 else 0
            pop(fr, im, CX + sx, 250, t, st, dur=0.3)
        if 3.4 <= t < 6.0: paste(fr, emoji('😰', 90), 600, 380, 1)
        return fr
    def music(sec):
        m = beat_track(sec, 100, style='lofi', key=1, seed=rnd, vol=0.6)
        for _, st in lines:   # nervous gulps
            n = int(0.25 * SR); tt = np.arange(n) / SR
            add(m, st + 0.1, np.sin(2 * np.pi * np.cumsum(500 - 1400 * tt) / SR) * np.exp(-tt * 14), 0.25)
        sfx_wahwah(m, 12.3)
        return m
    return dur, draw, music


def fmt_athome(F, rnd):
    """'We have Steelcase Leap at home.' The one that got away vs the one you got. Sad on purpose."""
    L = facts(ALL_DATA['steelcase-leap'])
    dur = 26.0
    gray = lambda im: ImageOps.grayscale(im.convert('RGB')).convert('RGBA')
    leap = hero_image(L); feego = hero_image(F)
    leap_gray = gray(leap)
    leap_card = rounded(cover(load_photo(L['photos'][0]), 280, 330).convert('RGBA'), 22) if L['photos'] else mascot((245, 158, 11), 280)
    feego_card = rounded(cover(load_photo(F['photos'][0]), 280, 330).convert('RGBA'), 22) if F['photos'] else mascot((232, 80, 91), 280)
    leap_card_g = gray(leap_card); leap_card_g.putalpha(leap_card.getchannel('A'))
    big = lambda s, sz=54, fg=(255, 255, 255): label(s, font('Black', sz), fg, None, 600, pad=(6, 4), stroke=5)
    mom_me = big('me: mom can we get a Steelcase Leap? 🥺', 50)
    price_tag = label('₱9,000 · Tier 1 Flagship', font('Black', 40), (20, 20, 20), (255, 214, 10, 255), 560, pad=(20, 10), r=14)
    mom = label('mom:', font('Bold', 40), (200, 200, 210), None, 600, pad=(0, 0))
    mom_says = label('we have Steelcase Leap at home.', font('Black', 58, SERIF_B), (255, 255, 255), None, 600, pad=(0, 0))
    at_home = big('Steelcase Leap at home:', 58)
    at_home_sub = label('Okamura Feego mesh · ₱5,000', font('Bold', 36), (255, 255, 255), (0, 0, 0, 170), 560, pad=(18, 8), r=12)
    head_l = label('what could have been', font('Black', 30), (255, 214, 10), None, 280, pad=(0, 0))
    head_r = label('what you have now', font('Black', 30), (200, 200, 210), None, 280, pad=(0, 0))
    leap_seat = f'{L["seat"][0]:g} cm' if L['seat'] else '?'
    rows = [('Tier 1 · Flagship', 'Tier 2 · Middle'),
            ('4D arms, move every way', 'fixed arms. forever.'),
            ('LiveBack back + lower-back firmness dial', 'fixed gray lumbar band'),
            ('new in Japan ¥186,980', 'new in Japan ¥132,220'),
            (f'seat goes down to {leap_seat}', 'made 2016. 2 yrs 9 mos past its 8-year JOIFA period'),
            ('V2? we’ll never know now', 'confirmed. very confirmed.'),
            ('₱9,000', '₱5,000')]
    rimgs = [(label(a, font('Bold', 27), (255, 230, 150), None, 280, pad=(0, 0), align='left'),
              label(b, font('Bold', 27), (225, 225, 232), None, 280, pad=(0, 0), align='left')) for a, b in rows]
    t_rows = 13.0; per = 1.35
    end1 = big('it was ₱4,000 away.', 60)
    end2 = label('#LeapAtHome #WhatCouldHaveBeen 🥀', font('Bold', 32), (230, 230, 240), None, 600, pad=(0, 0))
    rng = random.Random(rnd); drops = [(rng.random() * W, rng.random() * H, 18 + rng.random() * 30, 900 + rng.random() * 700) for _ in range(140)]
    def rain(fr, t, a=110):
        d = ImageDraw.Draw(fr)
        for x0, y0, ln, sp in drops:
            y = (y0 + t * sp) % (H + 60) - 60; x = x0 - (y - y0) * 0.12
            d.line([(x, y), (x - 4, y + ln)], fill=(200, 210, 230, a), width=2)
    def blue(fr, a=70):
        fr.alpha_composite(Image.new('RGBA', (W, H), (20, 40, 80, a)))
    def draw(t):
        if t < 3.6:   # the dream: the Leap, in colour
            fr = kenburns(leap, t, 3.6, 1.0, 1.08); shade(fr, 420, 360, 170)
            pop(fr, mom_me, CX, 230, t, 0.15, dur=0.3); pop(fr, price_tag, CX, 1080, t, 1.2, dur=0.3)
            return fr
        if t < 6.8:   # mom
            fr = Image.new('RGBA', (W, H), (8, 8, 12, 255))
            slide_in(fr, mom, CX, 520, t, 3.75, dur=0.4); slide_in(fr, mom_says, CX, 620, t, 4.4, dur=0.6)
            return fr
        if t < 11.2:  # the Leap at home
            fr = kenburns(feego, t - 6.8, 4.4, 1.0, 1.25); shade(fr, 380, 300, 180)
            sx, sy = shake(t, 10, 7.4)
            pop(fr, at_home, CX + sx, 220 + sy, t, 6.85, dur=0.25); pop(fr, at_home_sub, CX, 1090, t, 8.0, dur=0.3)
            return fr
        if t < 22.0:  # side by side
            fr = gradient((18, 22, 34), (6, 8, 14)); blue(fr, 30)
            paste(fr, leap_card_g if t > 20.5 else leap_card, 180, 270, 1); paste(fr, feego_card, 500, 270, 1)
            paste(fr, head_l, 180, 470, 1); paste(fr, head_r, 500, 470, 1)
            d = ImageDraw.Draw(fr); d.line([(340, 160), (340, 1230)], fill=(70, 75, 90), width=2)
            y = 530
            for k, (a, b) in enumerate(rimgs):
                st = t_rows - 1.8 + k * per
                if t >= st:
                    al = min(1, (t - st) / 0.4)
                    paste(fr, a, 40, y, al, anchor='tl'); paste(fr, b, 360, y, al, anchor='tl')
                y += max(a.height, b.height) + 26
            rain(fr, t, 60)
            return fr
        # the end: the Leap fades to grey in the rain
        k = min(1, (t - 22.0) / 1.5)
        fr = Image.blend(kenburns(leap, t - 22, 4, 1.08, 1.0).convert('RGB'), kenburns(leap_gray, t - 22, 4, 1.08, 1.0).convert('RGB'), k).convert('RGBA')
        blue(fr, int(60 + 60 * k)); shade(fr, 300, 420, 190); rain(fr, t, 140)
        slide_in(fr, end1, CX, 560, t, 22.6, dur=0.8); slide_in(fr, end2, CX, 700, t, 23.8, dur=0.8)
        return fr
    def music(sec):
        m = beat_track(sec, 66, style='sad', key=-3, seed=rnd, vol=0.9)
        sfx_wahwah(m, 6.9)
        for k in range(len(rows)): sfx_ding(m, t_rows - 1.8 + k * per, 660)
        return m
    return dur, draw, music

FORMATS = {'athome': fmt_athome, 'brainrot': fmt_brainrot, 'nervous': fmt_nervous, 'salesman': fmt_salesman, 'jokes': fmt_jokes, 'aislop': fmt_aislop, 'spin': fmt_spin, 'documentary': fmt_documentary,
           'mystery': fmt_mystery, 'dating': fmt_dating, 'news': fmt_news, 'pov': fmt_pov}

# ======================================================================
# music + sound effects, made from scratch
# ======================================================================
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def env_exp(n, rate): return np.exp(-np.arange(n) / SR * rate)

def add(buf, at, sig, vol=1.0):
    i = int(at * SR)
    if i >= len(buf) or i < 0: return
    n = min(len(sig), len(buf) - i); buf[i:i + n] += vol * sig[:n]

def tone(f, dur, kind='sine', rate=6):
    n = int(dur * SR); t = np.arange(n) / SR
    if kind == 'saw': s = 2 * ((f * t) % 1) - 1
    elif kind == 'square': s = np.sign(np.sin(2 * np.pi * f * t))
    elif kind == 'pluck': s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    else: s = np.sin(2 * np.pi * f * t)
    return s * env_exp(n, rate) * np.minimum(1, np.arange(n) / (SR * 0.004))

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
def snare():
    n = int(0.2 * SR); rng = np.random.default_rng(1)
    return (0.7 * rng.standard_normal(n) + 0.5 * np.sin(2 * np.pi * 190 * np.arange(n) / SR)) * env_exp(n, 22)
def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR); s = np.random.default_rng(2).standard_normal(n)
    return (s - np.concatenate([[0], s[:-1]])) * env_exp(n, 14 if open_ else 70) * 0.5
def clap():
    s = np.zeros(int(0.2 * SR)); rng = np.random.default_rng(3)
    for k in range(3): add(s, k * 0.01, rng.standard_normal(int(0.15 * SR)) * env_exp(int(0.15 * SR), 30))
    return s
def tambourine():
    n = int(0.12 * SR); s = np.random.default_rng(4).standard_normal(n); s = s - np.concatenate([[0], s[:-1]])
    return s * env_exp(n, 25) * (1 + 0.5 * np.sin(2 * np.pi * 30 * np.arange(n) / SR)) * 0.4

PROGS = {'pop': [(0, 4, 7), (-5, -1, 2), (-3, 0, 4), (-7, -3, 0)], 'major': [(0, 4, 7), (-3, 0, 4), (-7, -3, 0), (-5, -1, 2)],
         'minor': [(0, 3, 7), (-4, 0, 3), (-7, -4, 0), (-5, -2, 2)], 'jazz': [(2, 5, 9, 12), (7, 11, 14, 17), (0, 4, 7, 11), (0, 4, 7, 11)]}

def beat_track(sec, bpm, style='budots', key=0, seed=0, vol=1.0, start=0.0):
    """An original backing track. Styles: budots (bouncy Filipino dance-craze feel), techno, lofi, jazz,
    corporate, strings, news, gameshow, sad."""
    n = int(sec * SR); buf = np.zeros(n); rng = np.random.default_rng(seed)
    b = 60 / bpm; root = 48 + key
    prog = {'budots': 'pop', 'techno': 'minor', 'lofi': 'jazz', 'jazz': 'jazz', 'corporate': 'pop', 'strings': 'major',
            'news': 'minor', 'gameshow': 'major', 'sad': 'minor'}[style]
    P = PROGS[prog]
    scale = [0, 2, 4, 7, 9, 12, 14, 16] if prog != 'minor' else [0, 3, 5, 7, 10, 12, 15]
    hook = [scale[int(x)] for x in rng.integers(0, len(scale), 8)]
    t = start; bar = 0
    while t < sec:
        ch = P[bar % len(P)]
        for q in range(4):
            tb = t + q * b
            if style in ('budots', 'techno', 'news', 'gameshow'): add(buf, tb, kick(), 0.9)
            if style == 'budots':
                if q % 2 == 1: add(buf, tb, clap(), 0.35)
                add(buf, tb + b * 0.5, hat(), 0.5); add(buf, tb + b * 0.75, tambourine(), 0.5)
                add(buf, tb + b * 0.5, tone(hz(root - 12 + ch[0]), b * 0.45, 'saw', 9), 0.13)
                add(buf, tb + b * 0.5, tone(hz(root + 12 + ch[1]), b * 0.3, 'square', 14), 0.035)
                if q in (0, 2): add(buf, tb, tone(hz(root + 24 + hook[(bar * 2 + q // 2) % 8]), b * 0.9, 'pluck', 5), 0.08)
            elif style == 'techno':
                add(buf, tb + b * 0.5, hat(True), 0.35)
                if q % 2 == 1: add(buf, tb, clap(), 0.25)
                for s16 in range(4): add(buf, tb + s16 * b / 4, tone(hz(root - 12 + ch[0] + (12 if s16 == 2 else 0)), b / 4.2, 'saw', 18), 0.09)
                add(buf, tb, tone(hz(root + 12 + ch[q % 3]), b * 0.6, 'pluck', 8), 0.05)
            elif style == 'news':
                if q % 2 == 1: add(buf, tb, snare(), 0.35)
                add(buf, tb, tone(hz(root + ch[0]), b * 0.25, 'square', 20), 0.06); add(buf, tb + b / 2, hat(), 0.3)
                if q == 0:
                    for x in ch: add(buf, tb, tone(hz(root + 12 + x), b * 0.5, 'saw', 10), 0.04)
            elif style == 'gameshow':
                add(buf, tb + b / 2, hat(), 0.35); add(buf, tb, tone(hz(root - 12 + ch[0]), b * 0.8, 'pluck', 6), 0.12)
                if q % 2 == 1: add(buf, tb, snare(), 0.25)
                add(buf, tb, tone(hz(root + 24 + hook[(bar * 4 + q) % 8]), b * 0.5, 'square', 12), 0.03)
            elif style == 'lofi':
                if q in (0, 2): add(buf, tb, kick(), 0.5)
                if q in (1, 3): add(buf, tb + 0.02, snare(), 0.18)
                add(buf, tb + b * 0.55, hat(), 0.25)
                if q == 0:
                    for i, x in enumerate(ch): add(buf, tb + i * 0.015, tone(hz(root + x), b * 3.8, 'sine', 1.2), 0.05)
                if rng.random() < 0.6: add(buf, tb + b * 0.5, tone(hz(root + 12 + hook[(bar + q) % 8]), b * 0.8, 'pluck', 4), 0.05)
            elif style == 'jazz':
                walk = [ch[0], ch[1], ch[2], ch[1] + 1]
                add(buf, tb, tone(hz(root - 12 + walk[q]), b * 0.9, 'pluck', 5), 0.16)
                add(buf, tb + b * 0.66, hat(), 0.25); add(buf, tb, hat(True), 0.06)
                if q in (1, 3):
                    for x in ch: add(buf, tb, tone(hz(root + 12 + x), b * 0.4, 'sine', 9), 0.025)
            elif style == 'corporate':
                add(buf, tb, tone(hz(root + 24 + ch[q % 3]), b * 1.2, 'pluck', 4), 0.06)
                if q == 0:
                    for x in ch: add(buf, tb, tone(hz(root + x), b * 4, 'sine', 0.8), 0.04)
                if q in (0, 2): add(buf, tb, kick(), 0.4)
                if q in (1, 3): add(buf, tb, clap(), 0.15)
            elif style == 'sad':   # slow piano arpeggios over soft strings, no drums
                add(buf, tb, tone(hz(root + 12 + ch[q % 3] + (12 if q == 3 else 0)), b * 1.6, 'pluck', 2.2), 0.07)
                if q == 0:
                    add(buf, tb, tone(hz(root - 12 + ch[0]), b * 4, 'sine', 0.7), 0.10)
                    for x in ch:
                        for det in (-0.1, 0.1):
                            s_ = tone(hz(root + x + det), b * 4.2, 'saw', 0.4); s_ *= np.minimum(1, np.arange(len(s_)) / (SR * 1.2))
                            add(buf, tb, s_, 0.008)
            elif style == 'strings':
                if q == 0:
                    for x in ch:
                        for det in (-0.12, 0.12):
                            s_ = tone(hz(root + x + det), b * 4.2, 'saw', 0.5) * 1.0
                            s_ *= np.minimum(1, np.arange(len(s_)) / (SR * 0.8))
                            add(buf, tb, s_, 0.012)
                    add(buf, tb, tone(hz(root - 12 + ch[0]), b * 4, 'sine', 0.6), 0.08)
                if rng.random() < 0.5: add(buf, tb, tone(hz(root + 24 + hook[(bar * 4 + q) % 8]), b * 1.5, 'sine', 2.5), 0.03)
        t += 4 * b; bar += 1
    f = int(min(1.0, sec / 4) * SR); buf[-f:] *= np.linspace(1, 0, f)
    return buf * vol

def sfx_cash(buf, at):
    add(buf, at, tone(2093, 0.4, 'sine', 6), 0.25); add(buf, at + 0.08, tone(2637, 0.5, 'sine', 5), 0.25)
    n = int(0.12 * SR); add(buf, at, np.random.default_rng(5).standard_normal(n) * env_exp(n, 40), 0.2)
def sfx_boom(buf, at): add(buf, at, kick(), 1.2); add(buf, at, tone(55, 0.8, 'sine', 3), 0.5)
def sfx_ding(buf, at, f=1318): add(buf, at, tone(f, 0.8, 'sine', 4), 0.22); add(buf, at, tone(f * 2.01, 0.6, 'sine', 6), 0.08)
def sfx_whoosh(buf, at, vol=0.35):
    n = int(0.45 * SR); s = np.convolve(np.random.default_rng(6).standard_normal(n), np.ones(12) / 12, 'same')
    add(buf, max(0, at - 0.2), s * np.sin(np.linspace(0, np.pi, n)) ** 2, vol)
def sfx_rimshot(buf, at):
    add(buf, at, snare(), 0.5); add(buf, at + 0.18, snare(), 0.5)
    n = int(1.0 * SR); s = np.random.default_rng(7).standard_normal(n); s = s - np.concatenate([[0], s[:-1]])
    add(buf, at + 0.42, s * env_exp(n, 4) * 0.4, 0.5)
def sfx_wahwah(buf, at):
    for k, m in enumerate([62, 61, 60, 59]):
        n = int((0.4 if k < 3 else 1.0) * SR); tt = np.arange(n) / SR
        s = (2 * ((hz(m) * (1 + 0.01 * np.sin(2 * np.pi * 6 * tt)) * tt) % 1) - 1) * np.minimum(1, tt * 20) * np.exp(-tt * (2 if k < 3 else 1.2))
        add(buf, at + k * 0.42, s, 0.12)
def sfx_drumroll(buf, at, dur):
    k = 0.0
    while k < dur: add(buf, at + k, snare() * 0.6, 0.25 + 0.3 * k / dur); k += 0.045
def sfx_sting(buf, at):
    for x in (0, 4, 7, 12): add(buf, at, tone(hz(72 + x), 1.4, 'saw', 2), 0.05)
    add(buf, at, kick(), 1.0); add(buf, at, hat(True), 0.6)

def write_wav(sig, path):
    sig = sig / (np.abs(sig).max() + 1e-9) * 0.7
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((sig * 32767).astype(np.int16).tobytes())

# ======================================================================
# render
# ======================================================================
def render(cid, style, data, frames_only=False):
    F = facts(data[cid]); rnd = sum(map(ord, cid))
    dur, draw, music = FORMATS[style](F, rnd)
    if frames_only:
        out = '/tmp/chairtok-frames'; os.makedirs(out, exist_ok=True)
        for k, tt in enumerate([2.0, dur * 0.3, dur * 0.55, dur * 0.82]):
            draw(tt).convert('RGB').save(f'{out}/{cid}-{k}.jpg', quality=85)
        return out
    work = '/tmp/chairtok-' + cid; os.makedirs(work, exist_ok=True)
    vid = os.path.join(work, 'v.part.mp4')
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *ENC, vid], stdin=subprocess.PIPE)
    for k in range(int(round(dur * FPS))): p.stdin.write(draw(k / FPS).convert('RGB').tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit('ffmpeg failed: ' + cid)
    os.replace(vid, os.path.join(work, 'v.mp4'))
    wav = os.path.join(work, 'm.wav'); write_wav(music(dur), wav)
    os.makedirs(OUT, exist_ok=True)
    final = os.path.join(OUT, cid + '.mp4'); tmp = final[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(work, 'v.mp4'), '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '96k', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, final)
    draw(min(dur - 0.5, 2.5)).convert('RGB').save(os.path.join(OUT, cid + '.jpg'), quality=82)
    json.dump({'style': style}, open(os.path.join(OUT, cid + '.json'), 'w'))
    return final

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = '--frames' in sys.argv
    data = site_data()
    ALL_DATA.update(data)
    plan = [(c, s) for c, s in PLAN if not args or c in args or s in args]
    if not frames:  # feed order and format for the website
        os.makedirs(OUT, exist_ok=True)
        json.dump([{'id': c, 'style': s} for c, s in PLAN], open(os.path.join(OUT, 'feed.json'), 'w'), indent=1)
    for cid, style in plan:
        print(style.ljust(12), render(cid, style, data, frames), flush=True)
