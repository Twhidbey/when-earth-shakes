#!/usr/bin/env python3
"""One picture from Gemini's image model, with reference pictures.
  GEMINI_API_KEY=... python3 tools/make-image.py OUT.png "prompt text" ref1.png ref2.webp ... [--aspect 16:9] [--size 2K] [--model gemini-3-pro-image]
References are sent before the text, resized to at most 1536 px. Costs money (about 13-15 cents a 2K picture on the pro model)."""
import base64, io, json, os, sys, time, urllib.error, urllib.request
from PIL import Image
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
aspect, size, model = opt('--aspect', '16:9'), opt('--size', '2K'), opt('--model', 'gemini-3-pro-image')
out, prompt, refs = args[0], args[1], args[2:]
parts = []
for r in refs:
    im = Image.open(r).convert('RGB'); im.thumbnail((1536, 1536))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=88)
    parts.append({'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(b.getvalue()).decode()}})
parts.append({'text': prompt})
body = {'contents': [{'parts': parts}], 'generationConfig': {'responseModalities': ['TEXT', 'IMAGE'],
        'imageConfig': {'aspectRatio': aspect, 'imageSize': size}}}
req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
      data=json.dumps(body).encode(), headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'], 'Content-Type': 'application/json'})
for i in range(4):
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300)); break
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:500]
        if e.code in (429, 500, 503) and i < 3: time.sleep(15 * (i + 1)); continue
        sys.exit(f'{e.code}: {msg}')
got = False
for p in r['candidates'][0]['content']['parts']:
    if 'inlineData' in p:
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        open(out, 'wb').write(base64.b64decode(p['inlineData']['data'])); got = True
    elif 'text' in p:
        print('model says:', p['text'][:300])
print('saved' if got else 'NO IMAGE', out, r.get('usageMetadata', {}))
