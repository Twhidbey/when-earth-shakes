#!/usr/bin/env python3
"""Build the trailer rough cut from edit.json: stills with slow moves, verse cards,
and a placeholder sound bed made in code. Usage: python3 trailer/build.py [out.mp4]"""
import json, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
E = json.load(open(os.path.join(HERE, 'edit.json')))
FPS, (W, H) = E['fps'], E['size']
END = E['end']
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'rough-cut.mp4')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FONT_V = ImageFont.truetype(os.path.join(HERE, 'fonts', 'IMFeENit28P.ttf'), 46)
FONT_R = ImageFont.truetype(os.path.join(HERE, 'fonts', 'IMFeENrm28P.ttf'), 28)
FONT_T = ImageFont.truetype(os.path.join(HERE, 'fonts', 'Cinzel[wght].ttf'), 120)
try:
    FONT_T.set_variation_by_axes([600])
except Exception:
    pass

def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

# ---------- pictures ----------
CACHE = {}
def pic(name):
    if name not in CACHE:
        im = Image.open(os.path.join(ROOT, 'stills', name)).convert('RGB')
        if im.width > 3000:
            im = im.resize((3000, round(im.height * 3000 / im.width)), Image.LANCZOS)
        CACHE[name] = im
    return CACHE[name]

def frame_of(s, t):
    im = pic(s['file'])
    u = smooth((t - s['start']) / s['dur'])
    cx, cy, z = [a + (b - a) * u for a, b in zip(s['from'], s['to'])]
    # crop 16:9 window; zoom 1 = the picture's full width (or full height if narrower)
    bw = min(im.width, im.height * W / H) / z
    bh = bw * H / W
    x0 = min(max(cx * im.width - bw / 2, 0), im.width - bw)
    y0 = min(max(cy * im.height - bh / 2, 0), im.height - bh)
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))

def alpha_of(s, t):
    a = 1.0
    if s.get('fin', 0) > 0:
        a = min(a, (t - s['start']) / s['fin'])
    if s.get('fout', 0) > 0:
        a = min(a, (s['start'] + s['dur'] - t) / s['fout'])
    return min(max(a, 0.0), 1.0)

def text_layer(s, t):
    """verse in italic at the foot, the reference small under it; title in the middle"""
    if 'text' not in s and 'title' not in s:
        return None
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    tt = t - s['start']
    if 'title' in s:
        a = smooth((tt - 0.8) / 1.2) * min(1, (s['dur'] - tt) / 1.5)
        a = max(a, 0)
        tw = d.textlength(s['title'], font=FONT_T)
        d.text(((W - tw) / 2, H * 0.40), s['title'], font=FONT_T, fill=(235, 220, 195, int(255 * a)))
        t0, t1 = 2.4, s['dur'] - 1.2
    else:
        t0, t1 = 0.5, s['dur'] - 0.4
    if 'text' in s:
        a = smooth((tt - t0) / 0.6) * smooth((t1 - tt) / 0.5)
        if a > 0:
            y = H * (0.62 if 'title' in s else 0.80)
            tw = d.textlength(s['text'], font=FONT_V)
            # a soft dark band behind the words
            band = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(band).rectangle((0, y - 30, W, y + 110), fill=(0, 0, 0, int(110 * a)))
            band = band.filter(ImageFilter.GaussianBlur(40))
            lay = Image.alpha_composite(band, lay)
            d = ImageDraw.Draw(lay)
            d.text(((W - tw) / 2, y), s['text'], font=FONT_V, fill=(240, 228, 205, int(255 * a)))
            rw = d.textlength(s['tref'], font=FONT_R)
            d.text(((W - rw) / 2, y + 62), s['tref'], font=FONT_R, fill=(200, 185, 160, int(200 * a)))
    return lay

def render_video(path):
    n = int(END * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
                           '-crf', '20', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    black = Image.new('RGB', (W, H), (0, 0, 0))
    for i in range(n):
        t = i / FPS
        out = black.copy()
        for s in E['shots']:
            if s['start'] <= t < s['start'] + s['dur']:
                a = alpha_of(s, t)
                if a > 0:
                    out = Image.blend(out, frame_of(s, t), a) if a < 1 else frame_of(s, t)
                lay = text_layer(s, t)
                if lay is not None:
                    out = Image.alpha_composite(out.convert('RGBA'), lay).convert('RGB')
        ff.stdin.write(out.tobytes())
        if i % 240 == 0:
            print(f'  video {t:5.1f}s', flush=True)
    ff.stdin.close()
    ff.wait()

# ---------- sound (placeholder, made in code) ----------
SR = 44100
rng = np.random.default_rng(7)

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)

def env(n, att, rel):
    e = np.ones(n)
    a, r = int(att * SR), int(rel * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] *= np.linspace(1, 0, r)
    return e

def add(buf, t, x, g=1.0):
    i = int(t * SR)
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += g * x[:j - i]

def noise(d):
    return rng.standard_normal(int(d * SR))

def boom(d=2.5, f0=70, f1=28):
    n = int(d * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 3)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.6)
    return s + 0.25 * lowpass(noise(d), 200) * np.exp(-tt * 4)

def click(d=0.05, fc=3000):
    tt = np.arange(int(d * SR)) / SR
    return noise(d) * np.exp(-tt * 120) * 0.6

def render_audio(path):
    n = int(END * SR)
    L = np.zeros(n)
    tt = np.arange(n) / SR
    # radio static and tuning at the open, crackle bed through act 1
    st = lowpass(noise(3.2), 3500) - lowpass(noise(3.2), 400)
    tun = np.sin(2 * np.pi * np.cumsum(900 + 700 * np.sin(np.linspace(0, 5, len(st)))) / SR) * 0.08
    add(L, 0.0, (st * 0.5 + tun) * env(len(st), 0.05, 1.0), 0.6)
    crack = np.zeros(int(22 * SR))
    for k in rng.integers(0, len(crack) - 400, 260):
        crack[k:k + 200] += click(200 / SR) * rng.uniform(0.2, 1)
    add(L, 2.5, crack * env(len(crack), 1, 3), 0.25)
    # wind
    w = lowpass(noise(21), 500) * (0.6 + 0.4 * np.sin(np.linspace(0, 9, int(21 * SR))))
    add(L, 3.0, w * env(len(w), 2, 1.5), 0.5)
    # deep rumble rising through act 1, stopping dead at 24.0
    r = lowpass(lowpass(noise(15), 60), 60)
    r = r / np.abs(r).max()
    add(L, 9.0, r * np.linspace(0.1, 1, len(r)), 0.9)
    # seismometer needle ticking faster
    t = 13.6
    while t < 18.0:
        add(L, t, click(0.03), 0.5)
        t += 0.32 - 0.22 * (t - 13.6) / 4.4
    L[int(24.0 * SR):int(25.0 * SR)] = 0
    # act 2: crash, drone, heartbeat
    add(L, 25.0, boom(3.0), 1.0)
    d = (np.sin(2 * np.pi * 55 * tt) + 0.6 * np.sin(2 * np.pi * 82.4 * tt) + 0.3 * np.sin(2 * np.pi * 110.5 * tt))
    d *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * tt)
    m = np.clip((tt - 26) / 10, 0, 1) * (tt < 70) + np.clip((tt - 78) / 2, 0, 1) * (tt < 84) * 0.6
    L += 0.18 * d * m
    def beat(t0, t1, period, g):
        t = t0
        while t < t1:
            add(L, t, boom(0.5, 60, 40), g)
            add(L, t + 0.22, boom(0.4, 55, 38), g * 0.6)
            t += period
    beat(30.0, 50.0, 1.25, 0.55)
    beat(50.0, 58.0, 0.85, 0.7)
    # act 3 sound effects
    add(L, 45.2, lowpass(noise(1.6), 300) * env(int(1.6 * SR), 0.6, 0.9), 0.5)          # breath
    add(L, 48.0, lowpass(noise(2.0), 2500) * env(int(2.0 * SR), 0.1, 0.5), 0.3)         # fire crackle
    add(L, 54.05, click(0.08) * 3, 0.8); add(L, 54.12, boom(0.4, 300, 120), 0.4)       # visor clank
    add(L, 56.1, click(0.05), 0.8); add(L, 56.5, click(0.05), 0.8); add(L, 57.0, click(0.07) * 2, 1.0)  # shells, breech
    beat(58.0, 69.0, 0.5, 0.8)                                                           # the beat drops
    fr = lowpass(noise(6), 900) * env(int(6 * SR), 1.0, 1.0)
    add(L, 60.0, fr, 0.7)                                                                # fire roar
    add(L, 66.4, noise(0.25) * np.exp(-np.arange(int(0.25 * SR)) / SR * 18), 1.0)       # shotgun blast
    add(L, 66.4, boom(1.5, 90, 35), 1.0)
    ro = lowpass(noise(2.2), 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * np.arange(int(2.2 * SR)) / SR))
    add(L, 68.0, ro * env(len(ro), 0.1, 1.2), 1.2)                                       # roar
    a, b = int(69.6 * SR), int(70.0 * SR)
    L[a:b] *= np.linspace(1, 0, b - a)
    L[int(70.0 * SR):int(78.0 * SR)] *= 0                                                # silence
    for t in (70.8, 71.9, 72.6, 74.1, 75.4, 76.9):                                      # drips
        add(L, t, np.sin(2 * np.pi * np.linspace(1400, 700, 2000).cumsum() / SR) * np.exp(-np.arange(2000) / 300), 0.25)
    add(L, 78.0, boom(4.0, 45, 30), 0.9)                                                 # the low note
    add(L, 85.5, boom(5.0, 60, 25), 1.0)                                                 # title hit
    cr = np.zeros(int(7 * SR))
    for k in rng.integers(0, len(cr) - 400, 90):
        cr[k:k + 200] += click(200 / SR)
    add(L, 86.0, cr * np.linspace(1, 0, len(cr)), 0.2)
    L /= max(1e-9, np.abs(L).max()) / 0.85
    st = np.stack([L, L], 1)
    pcm = (st * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes(pcm.tobytes())

if __name__ == '__main__':
    vid = OUT + '.video.mp4'
    wav = OUT + '.wav'
    print('sound...'); render_audio(wav)
    print('pictures...'); render_video(vid)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', OUT], check=True)
    os.remove(vid); os.remove(wav)
    print('done:', OUT)
