#!/usr/bin/env python3
"""Build the trailer rough cut from edit.json: stills with slow moves, verse cards,
and a placeholder sound bed made in code. Usage: python3 trailer/build.py [out.mp4]"""
import json, os, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    """time of a cue (a story moment marked in edit.json) or of the first shot whose file starts with name"""
    for s in E['shots']:
        if s.get('cue') == name:
            return s['start'] + off
    for s in E['shots']:
        if s['file'].startswith(name):
            return s['start'] + off
    raise KeyError(name)

def end_of(name):
    for s in E['shots']:
        if s.get('cue') == name:
            return s['start'] + s['dur']
    raise KeyError(name)

def rec(name, speed=1.0):
    """a real recording from trailer/sfx (see its CREDITS.md), optionally slowed (lower and bigger)"""
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', os.path.join(HERE, 'sfx', name), '-af',
                          f'asetrate={int(SR * speed)},aresample={SR}', '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype='<f4').astype(float)
    return x / max(1e-9, np.abs(x).max())

def loop(x, d, fade=0.4):
    n = int(d * SR); out = np.zeros(n); i = 0
    while i < n:
        k = min(len(x), n - i); out[i:i + k] += x[:k]; i += k
    return out * env(n, fade, fade)

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
    L = np.zeros(n)          # sound effects
    V = np.zeros(n)          # voice
    def add(buf, t, x, g=1.0):
        i = int(t * SR); j = min(len(buf), i + len(x))
        if j > i: buf[i:j] += g * x[:j - i]
    def boomat(t, *a, g=1.0): add(L, t, boom(*a), g)
    # the voice, each line with a faint radio hum and crackle under it
    for s in E['shots']:
        if 'vo' in s:
            v = voice(s['text']); v = v / max(1e-9, np.abs(v).max()) * 0.9
            t0 = s['start'] + s['vo']
            k = np.arange(len(v) + int(0.6 * SR)) / SR
            hum = 0.012 * (np.sin(2 * np.pi * 60 * k) + 0.5 * np.sin(2 * np.pi * 120 * k))
            cr = np.zeros(len(k))
            for q in rng.integers(0, len(k) - 400, max(1, int(len(k) / SR * 14))):
                cr[q:q + 200] += click(200 / SR) * rng.uniform(0.1, 0.5)
            add(V, t0 - 0.2, hum * env(len(k), 0.15, 0.3) + 0.08 * cr)
            add(V, t0, v)
    # opening: a radio tuning in, then wind over the fields
    st = lowpass(noise(1.2), 3500) - lowpass(noise(1.2), 400)
    tun = np.sin(2 * np.pi * np.cumsum(900 + 700 * np.sin(np.linspace(0, 3, len(st)))) / SR) * 0.08
    add(L, 0.0, (st * 0.5 + tun) * env(len(st), 0.05, 0.4), 0.5)
    d = at('crash') - 0.6
    w = lowpass(noise(d), 500) * (0.6 + 0.4 * np.sin(np.linspace(0, 5, int(d * SR))))
    add(L, 0.6, w * env(len(w), 1.0, 0.3), 0.4)
    # the crash: two real explosions, one slowed right down for size
    ex_a, ex_b = rec('explosion-a.flac'), rec('explosion-b.flac')
    add(L, at('crash'), rec('explosion-a.flac', 0.55), 1.0)
    add(L, at('crash', 0.05), ex_b, 0.5)
    # real grass fire: a quiet bed from the burning field, swelling at the boy, roaring through the fire run
    fire, fire_lo = rec('grass-fire.flac'), rec('grass-fire.flac', 0.5)
    t0 = at('14-'); d = at('rise') - t0
    add(L, t0, loop(fire, d, 0.5) * np.linspace(0.3, 0.8, int(d * SR)), 0.6)
    add(L, t0, loop(fire_lo, d, 0.5), 0.35)
    t0, t1 = at('fire'), at('water', 0.3)
    add(L, t0, loop(fire, t1 - t0, 0.15), 0.9)
    add(L, t0, loop(fire_lo, t1 - t0, 0.15), 0.8)
    add(L, t0, rec('explosion-a.flac', 0.45), 0.9)                     # the fire bursts up
    add(L, at('35-'), ex_a, 0.5)
    # into the water: the fire cut off under a deep slowed hit
    add(L, at('water'), rec('explosion-b.flac', 0.35), 0.6)
    # the title: a slowed explosion under the final boom, a breath of fire after it
    add(L, at('title', 1.0), rec('explosion-a.flac', 0.4), 0.8)
    add(L, at('title', 1.5), loop(fire_lo, END - at('title', 1.5), 1.5), 0.25)
    # a hit on every cut from the crash to the fire, strong and soft by turns
    i0 = [k for k, s in enumerate(E['shots']) if s.get('cue') == 'crash'][0]
    i1 = [k for k, s in enumerate(E['shots']) if s.get('cue') == 'fire'][0]
    for j, s in enumerate(E['shots'][i0 + 1:i1]):
        w = lowpass(noise(0.35), 1200) * np.linspace(0, 1, int(0.35 * SR)) ** 3
        add(L, s['start'] - 0.35, w, 0.3)
        boomat(s['start'], 0.8, 75, 38, g=0.7 if j % 2 == 0 else 0.4)
    # the drop before the fire: effects go silent (the music keeps playing, low)
    a, b = int(end_of('gear') * SR), int(at('fire') * SR)
    a = int(at('fire', -0.8) * SR); f = int(0.05 * SR)
    L[a:a + f] *= np.linspace(1, 0, f); L[a + f:b] = 0
    # the music (trailer/score.py), never silent
    from score import score
    S = score(at, end_of, n)
    duck = (np.abs(V) > 0.02).astype(float)
    k = int(0.3 * SR); duck = np.convolve(duck, np.ones(k) / k, 'same').clip(0, 1)
    G = np.ones(n)
    def ramp(t0, t1, g0, g1):
        a, b = int(t0 * SR), int(t1 * SR); G[a:b] = np.linspace(g0, g1, b - a)
    ramp(at('fire'), at('water'), 1.9, 2.3)
    ramp(at('walk'), at('walk', 2.4), 1.5, 1.2)
    ramp(at('title', 1.0), at('title', 4.0), 1.8, 1.3); ramp(at('title', 4.0), END, 1.3, 1.0)
    L /= max(1e-9, np.abs(L).max()) / 0.6
    M = (L * (1 - 0.45 * duck) + 0.65 * S * (1 - 0.45 * duck)) * G + V
    M /= max(1e-9, np.percentile(np.abs(M), 99.95)) / 0.75
    M = np.tanh(1.3 * M) / np.tanh(1.3) * 0.85                # a soft limiter: loud, never clipped
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
