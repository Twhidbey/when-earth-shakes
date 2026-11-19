#!/usr/bin/env python3
"""Record the trailer's voiceover (Job 41, KJV) with Gemini TTS in a designed deep voice.
GEMINI_API_KEY must be set (never stored in the repo). Records only lines that have no recording yet.
  python3 tools/make-voice.py            record missing lines
  python3 tools/make-voice.py --design   design the narrator voice (prints its id; put it in VOICE)
Each recording is checked by having a Gemini model write down what it hears."""
import base64, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request, time
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'trailer', 'voice')
API = 'https://generativelanguage.googleapis.com/v1beta'
TTS, EAR = 'gemini-3.8-flash-tts', 'gemini-3.8-flash'
KEY = os.environ.get('GEMINI_API_KEY', '')
VOICE = os.environ.get('WES_VOICE', 'voice_fbzr3xumfwod')   # designed Nov 19 2026, expires Nov 2027
DESC = ("An older American man, about sixty, with a very deep, low bass voice, a little gravelly and weathered, from the "
        "rural Midwest. He reads scripture slowly and gravely, with long pauses, like an old-time radio preacher reading "
        "by lamplight: solemn, quiet, unhurried, full of awe and warning, never shouting.")
STYLE = '[very slow, deep, grave, quiet awe]'

def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'x-goog-api-key': KEY, 'Content-Type': 'application/json'})
    for i in range(5):
        try: return json.load(urllib.request.urlopen(req, timeout=180))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (429, 500, 503) and i < 4: time.sleep(10 * (i + 1)); continue
            sys.exit(f'{e.code}: {msg}')

def fname(text): return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:48] + '.mp3'
def words(s): return re.sub(r'[^a-z ]', '', s.lower().replace('-', ' ')).split()

def lines():
    e = json.load(open(os.path.join(ROOT, 'trailer', 'edit.json')))
    return [s['text'] for s in e['shots'] if 'text' in s]

def record(text, dest):
    for attempt in range(3):
        g = call(f'/models/{TTS}:generateContent', {'contents': [{'parts': [{'text': STYLE + ' ' + text}]}],
                 'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': {'voiceConfig': {'voice': VOICE}}}})
        wav = base64.b64decode(g['candidates'][0]['content']['parts'][0]['inlineData']['data'])
        with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as f: f.write(wav)
        cut = 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05'
        fmt = ['-f', 's16le', '-ar', '24000', '-ac', '1'] if not wav[:4] == b'RIFF' else []
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *fmt, '-i', f.name, '-af', f'{cut},areverse,{cut},areverse',
                        '-ac', '1', '-ar', '24000', '-b:a', '96k', dest], check=True)
        os.unlink(f.name)
        heard = call(f'/models/{EAR}:generateContent', {'contents': [{'parts': [
            {'inlineData': {'mimeType': 'audio/mp3', 'data': base64.b64encode(open(dest, 'rb').read()).decode()}},
            {'text': 'Write down exactly the words spoken in this recording, and nothing else.'}]}]})
        heard = heard['candidates'][0]['content']['parts'][0].get('text', '')
        if words(heard) == words(text): return attempt + 1
        print(f'   heard "{heard.strip()}", trying again')
    print(f'   kept the last take of: {text}')
    return 3

if __name__ == '__main__':
    if not KEY: sys.exit('Set GEMINI_API_KEY')
    if '--design' in sys.argv:
        v = call('/voices', {'model': f'models/{TTS}', 'type': 'prompted', 'store': True, 'prompted': {'input': DESC}})
        print(json.dumps(v)[:600]); sys.exit()
    if not VOICE: sys.exit('Set WES_VOICE to the designed voice id')
    os.makedirs(OUT, exist_ok=True)
    for t in lines():
        dest = os.path.join(OUT, fname(t))
        if os.path.exists(dest): continue
        n = record(t, dest)
        print(f'{n} take(s): {t}')
