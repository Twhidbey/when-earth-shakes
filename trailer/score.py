"""An original score made in code, in the manner of big trailer music (Inception, Interstellar):
an organ that swells, low brass 'braams' that hit and ring, rising Shepard tones before the hits,
a pulsing ostinato through the fire, a hard silence before the sword. Nothing is sampled or copied.
score(at, n) returns a mono float array; at(name, offset) gives a shot's start time."""
import numpy as np
from scipy.signal import fftconvolve

SR = 44100
rng = np.random.default_rng(11)

def hz(note):
    """'A2' -> 110.0 (sharps as 'G#3')"""
    names = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
    n, o = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)

def put(buf, t, x, g=1.0):
    i = int(t * SR); j = min(len(buf), i + len(x))
    if j > i and i >= 0:
        buf[i:j] += g * x[:j - i]

def organ(notes, dur, att=None, rel=1.2):
    """church-organ-like chord: pipes at the note and its octaves, slow swell, a little air"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for note in notes:
        f = hz(note)
        for k, a in ((1, 1.0), (2, .5), (3, .18), (4, .22), (6, .06), (8, .08)):
            if f * k < 8000:
                x += a * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.3)) * (1 + .002 * np.sin(2 * np.pi * 5.5 * t))
    att = dur * .45 if att is None else att
    e = np.clip(t / max(att, 1e-3), 0, 1) ** 1.6
    r = int(min(rel, dur) * SR); e[-r:] *= np.linspace(1, 0, r) ** 1.5
    return x * e / (len(notes) * 1.6)

def braam(dur=4.5, bright=1.0):
    """low brass cluster: detuned saw stacks, the filter bursting open then closing, driven hard"""
    n = int(dur * SR); t = np.arange(n) / SR
    fc = 180 + 2200 * bright * np.exp(-t / .45) + 250 * np.exp(-t / 2.5)
    x = np.zeros(n)
    for note, g in (('A1', 1.0), ('A2', .8), ('E2', .7), ('C3', .45), ('E3', .35)):
        for det in (-.004, .0, .005):
            f = hz(note) * (1 + det)
            ph = rng.uniform(0, 6.3)
            for k in range(1, 48):
                if f * k > 6000: break
                w = np.exp(-(f * k) / fc) / k
                x += g * w * np.sin(2 * np.pi * f * k * t + ph * k)
    e = np.minimum(t / .05, 1) * (0.55 + 0.45 * np.exp(-t / .8))
    r = int(1.8 * SR); e[-r:] *= np.linspace(1, 0, r) ** 2
    x = np.tanh(2.2 * x * e / 6)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 40 * np.exp(-t * 4)) / SR) * np.exp(-t * 1.2)
    return x + .9 * sub

def shepard(dur, up=True):
    """an endlessly rising tone: octave-spaced sines gliding up, faded at both ends of the range"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for o in range(8):
        lf = np.log2(55) + ((o + (t / dur) * 1.5 * (1 if up else -1)) % 8)
        f = 2 ** lf
        a = np.exp(-((lf - np.log2(440)) ** 2) / 2.2)
        x += a * np.sin(2 * np.pi * np.cumsum(f) / SR)
    noise = rng.standard_normal(n)
    noise = fftconvolve(noise, np.ones(40) / 40, 'same')
    x = x * .5 + noise * .6 * (t / dur) ** 2
    return x * (t / dur) ** 1.8

def hit(g=1.0):
    """a taiko-like drum: pitched thump and a skin slap"""
    n = int(1.2 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 5)
    slap = rng.standard_normal(n) * np.exp(-t * 60) * .4
    return g * (body + slap)

def pulse(note, dur, step, accent=4):
    """a staccato low-string ostinato on one note"""
    n = int(dur * SR); x = np.zeros(n)
    k = int(step * SR * .7); tt = np.arange(k) / SR
    f = hz(note)
    tone = sum(np.sin(2 * np.pi * f * m * tt) / m for m in range(1, 9)) * np.exp(-tt * 9)
    i = 0
    while i * step < dur:
        put(x, i * step, tone, 1.0 if i % accent == 0 else .6)
        i += 1
    return x

def reverb(x, secs=2.2, wet=.35):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / secs)
    ir = fftconvolve(ir, np.ones(25) / 25, 'same')
    y = fftconvolve(x, ir)[:len(x)]
    y /= max(1e-9, np.abs(y).max()) / max(1e-9, np.abs(x).max())
    return (1 - wet) * x + wet * y

def score(at, end_of, n):
    """at(cue, offset) and end_of(cue) come from edit.json, so the music follows the cut"""
    S = np.zeros(n)
    T = n / SR
    def chords(seq, t_end, g0, step):
        for i, (ch, t0) in enumerate(seq):
            t1 = seq[i + 1][1] if i + 1 < len(seq) else t_end
            put(S, t0, organ(ch, t1 - t0 + .3, att=.5, rel=.3), g0 + step * i)
    Am, F, C, G, E = ['A2', 'C3', 'E3', 'A3'], ['F2', 'A2', 'C3', 'F3'], ['C3', 'E3', 'G3', 'C4'], ['G2', 'B2', 'D3', 'G3'], ['E2', 'G#2', 'B2', 'E3']
    # under everything, start to end: a low organ A that never stops
    put(S, .3, organ(['A1', 'E2', 'A2'], T - .3, att=3.0, rel=2.5), .22)
    # the hush
    put(S, at('open'), organ(['E3', 'A3'], at('crash') - at('open') + .3, att=2.5, rel=.3), .25)
    put(S, at('10-'), organ(['E5'], at('crash') - at('10-') + .2, att=1.0, rel=.3), .1)
    # the sign
    put(S, at('crash'), braam(4.5, .7), .55)
    chords([(Am, at('crash')), (F, at('15-')), (C, at('14-')), (E, at('boyfire'))], at('rise'), .35, .08)
    # the rise
    put(S, at('rise'), braam(5.0, .9), .7)
    chords([(Am, at('rise')), (F, at('46-')), (C, at('34-')), (G, at('30-')), (Am, at('gear')), (F, at('44-'))], at('fire', -.8), .4, .05)
    put(S, at('46-'), pulse('A1', at('gear') - at('46-'), .6), .25)
    put(S, at('gear'), pulse('A1', at('fire', -.8) - at('gear'), .3), .35)
    put(S, at('30-'), shepard(at('fire', -.8) - at('30-')), .45)
    # the drop: only a held high note over the low bed, pulled in toward the hit
    put(S, at('fire', -.8), organ(['E4', 'A4'], .8, att=.7, rel=.02), .3)
    # the fire
    t0, t1 = at('fire'), at('water')
    put(S, t0, braam(5.5, 1.2), 1.0)
    put(S, at('35-'), braam(3.5, 1.0), .6)
    k = 0
    while t0 + k * .6 < t1:
        put(S, t0 + k * .6, hit(1.0 if k % 2 == 0 else .6), .9); k += 1
    put(S, t0, pulse('A2', t1 - t0, .15), .35)
    put(S, t0, organ(Am + ['E4'], at('35-') - t0 + .2, att=.3, rel=.2), .55)
    put(S, at('35-'), organ(F + ['C4'], t1 - at('35-') + .3, att=.2, rel=.3), .6)
    # the water and the sword: quiet and high, then rising
    put(S, at('water'), organ(['A4', 'C5', 'E5'], at('sword') - at('water') + .4, att=1.0, rel=.5), .22)
    put(S, at('sword'), organ(['F3', 'A3', 'C4', 'F4'], at('walk') - at('sword') + .2, att=.8, rel=.2), .35)
    put(S, at('sword'), shepard(at('walk') - at('sword')), .35)
    put(S, at('walk'), braam(4.0, 1.0), .85)
    put(S, at('walk'), organ(['C3', 'E3', 'G3', 'C4', 'G4'], at('title', 1.0) - at('walk'), att=.3, rel=.6), .5)
    # the title
    put(S, at('title', 1.0), braam(6.0, 1.1), 1.0)
    put(S, at('title', 1.0), organ(['A1', 'A2', 'E3', 'A3'], T - at('title', 1.0), att=.4, rel=3.0), .5)
    S = reverb(S)
    return S / max(1e-9, np.abs(S).max())
