#!/usr/bin/env python3
"""Build the trailer rough cut from edit.json: stills with slow moves, verse cards,
and a placeholder sound bed made in code. Usage: python3 trailer/build.py [out.mp4]"""
import json, os, re, subprocess, sys, wave
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
    if 'text' in s and E.get('show_text', True):
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

def at(name, off=0.0):
    """time of a shot's start (by the start of its file name) plus an offset: sound cues follow the shots"""
    for s in E['shots']:
        if s['file'].startswith(name):
            return s['start'] + off
    raise KeyError(name)

def voice(text):
    """a recorded line, made to sound like an old radio: narrow band, a little drive, warm"""
    src = os.path.join(HERE, 'voice', re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:48] + '.mp3')
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', src, '-af',
        'silenceremove=stop_periods=-1:stop_duration=0.45:stop_threshold=-42dB,'
        f'atempo={E.get("vo_speed", 1.0)},highpass=f=220,lowpass=f=3400,acompressor=threshold=-20dB:ratio=4:makeup=6,'
        'equalizer=f=1400:t=q:w=1.2:g=5,volume=2.2,asoftclip=type=tanh,highpass=f=180,lowpass=f=3800',
        '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<f4').astype(float)

def render_audio(path):
    n = int(END * SR)
    L = np.zeros(n)          # sound bed
    V = np.zeros(n)          # voice
    tt = np.arange(n) / SR
    def add(buf, t, x, g=1.0):
        i = int(t * SR); j = min(len(buf), i + len(x))
        if j > i: buf[i:j] += g * x[:j - i]
    def boomat(t, *a, g=1.0): add(L, t, boom(*a), g)
    # voice lines, each with a faint radio hum and crackle under it
    for s in E['shots']:
        if 'vo' in s:
            v = voice(s['text'])
            v = v / max(1e-9, np.abs(v).max()) * 0.9
            t0 = s['start'] + s['vo']
            k = np.arange(len(v) + int(0.6 * SR)) / SR
            hum = 0.012 * (np.sin(2 * np.pi * 60 * k) + 0.5 * np.sin(2 * np.pi * 120 * k))
            cr = np.zeros(len(k))
            for q in rng.integers(0, len(k) - 400, max(1, int(len(k) / SR * 14))):
                cr[q:q + 200] += click(200 / SR) * rng.uniform(0.1, 0.5)
            add(V, t0 - 0.2, hum * env(len(k), 0.15, 0.3) + 0.08 * cr)
            add(V, t0, v)
    # 1. the hush: a radio tuning in, wind, a rumble rising, the needle ticking
    st = lowpass(noise(1.2), 3500) - lowpass(noise(1.2), 400)
    tun = np.sin(2 * np.pi * np.cumsum(900 + 700 * np.sin(np.linspace(0, 3, len(st)))) / SR) * 0.08
    add(L, 0.0, (st * 0.5 + tun) * env(len(st), 0.05, 0.4), 0.6)
    a1 = at('12-')
    w = lowpass(noise(a1), 500) * (0.6 + 0.4 * np.sin(np.linspace(0, 5, int(a1 * SR))))
    add(L, 0.6, w * env(len(w), 1.0, 0.3), 0.5)
    r0 = at('47-'); r = lowpass(lowpass(noise(a1 - r0), 60), 60); r /= np.abs(r).max()
    add(L, r0, r * np.linspace(0.1, 1, len(r)), 0.9)
    t, t1 = at('11-', 0.1), at('08-', 1.1)
    while t < t1:
        add(L, t, click(0.03), 0.5); t += max(0.07, 0.28 - 0.21 * (t - at('11-')) / 2.6)
    # 2. the sign: a crash, the drone, fire; a breath of silence before the bed
    boomat(at('12-'), 3.0, g=1.0)
    d = (np.sin(2 * np.pi * 55 * tt) + 0.6 * np.sin(2 * np.pi * 82.4 * tt) + 0.3 * np.sin(2 * np.pi * 110.5 * tt))
    d *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * tt)
    m = np.clip((tt - at('12-', .5)) / 4, 0, 1) * (tt < at('36b')) + np.clip((tt - at('37-')) / 2, 0, 1) * (tt < at('29-')) * 0.6
    L += 0.18 * d * m
    add(L, at('14-'), lowpass(noise(3.0), 2500) * env(int(3.0 * SR), 0.1, 0.5), 0.35)          # fire crackle
    a, b = int((at('16-') - 0.5) * SR), int(at('16-') * SR)
    L[a:b] *= np.linspace(1, 0, b - a) ** 2
    def beat(t0, t1, period, g):
        t = t0
        while t < t1:
            boomat(t, 0.5, 60, 40, g=g); boomat(t + 0.22, 0.4, 55, 38, g=g * 0.6); t += period
    beat(at('16-'), at('22-'), 1.1, 0.6)                                                        # heartbeat
    # 3. the gear: visor, shells, the breech; the beat drops into the fire
    add(L, at('22-', 0.05), click(0.08) * 3, 0.8); boomat(at('22-', 0.12), 0.4, 300, 120, g=0.4)
    add(L, at('23-', 0.1), click(0.05), 0.8); add(L, at('23-', 0.4), click(0.05), 0.8); add(L, at('23-', 0.75), click(0.07) * 2, 1.0)
    beat(at('22-'), at('25-'), 0.75, 0.7)
    beat(at('25-'), at('36-', 0.9), 0.4, 0.85)
    fr = lowpass(noise(3.2), 900) * env(int(3.2 * SR), 0.2, 0.4); add(L, at('34-'), fr, 0.8)  # fire roar
    sp = lowpass(noise(0.6), 1500) * env(int(0.6 * SR), 0.01, 0.4); add(L, at('36-', 0.1), sp, 0.7)  # splash and hiss
    # 4. the hold: silence, drips, the low note, the title hit
    a, b = int((at('36-', 0.95)) * SR), int(at('37-', 0.3) * SR)
    L[a:b] = 0
    for o in (0.4, 1.2, 1.7):
        add(L, at('36b', o), np.sin(2 * np.pi * np.linspace(1400, 700, 2000).cumsum() / SR) * np.exp(-np.arange(2000) / 300), 0.25)
    boomat(at('39-'), 3.0, 45, 30, g=0.8)
    boomat(at('29-', 1.0), 5.0, 60, 25, g=1.0)
    cr = np.zeros(int(5 * SR))
    for k in rng.integers(0, len(cr) - 400, 70): cr[k:k + 200] += click(200 / SR)
    add(L, at('29-', 1.5), cr * np.linspace(1, 0, len(cr)), 0.2)
    # mix: the bed ducks under the voice
    L /= max(1e-9, np.abs(L).max()) / 0.6
    a, b = int(at('25-', 0.5) * SR), int(at('36-', 0.95) * SR)
    L[a:b] *= np.linspace(1.4, 2.4, b - a)                   # the fire run is the loudest part
    duck = (np.abs(V) > 0.02).astype(float)
    k = int(0.3 * SR); duck = np.convolve(duck, np.ones(k) / k, 'same').clip(0, 1)
    M = L * (1 - 0.55 * duck) + V
    M /= max(1e-9, np.abs(M).max()) / 0.9
    pcm = (np.stack([M, M], 1) * 32767).astype('<i2')
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
