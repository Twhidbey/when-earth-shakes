"""Animate one still into a short clip on Modal (rented GPU), with Wan 2.2 image-to-video.

Needs MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment (set on the cloud environment, never in the repo).
  modal run tools/animate_modal.py --still stills/12-plume_of_smoke2.png --prompt "the smoke column billows ..." --out clips/12-smoke.mp4
Options: --frames 81 (about 5 s at 16 fps), --seed 1, --model 5b|14b.
The 5B model (Wan2.2-TI2V-5B, 1280x704) is the cheap test; 14b (Wan2.2-I2V-A14B, 1280x720) is the quality one.
Weights are cached in a Modal volume, so only the first run downloads them."""
import io
import modal

app = modal.App("when-earth-shakes-animate")
cache = modal.Volume.from_name("wes-hf-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
         .apt_install("ffmpeg")
         .pip_install("torch==2.5.1", "diffusers>=0.35.0", "transformers>=4.49", "accelerate", "ftfy",
                      "imageio[ffmpeg]", "pillow", "sentencepiece")
         .env({"HF_HOME": "/cache"}))

MODELS = {"5b": "Wan-AI/Wan2.2-TI2V-5B-Diffusers", "14b": "Wan-AI/Wan2.2-I2V-A14B-Diffusers"}
NEG = ("camera shake, zoom, cut, scene change, text, watermark, extra limbs, deformed hands, morphing face, "
       "flicker, blurry, low quality, cartoon, 3d render")


@app.function(image=image, gpu="H100", volumes={"/cache": cache}, timeout=60 * 30)
def generate(still: bytes, prompt: str, frames: int = 81, seed: int = 1, model: str = "5b") -> bytes:
    import torch
    from diffusers import WanImageToVideoPipeline, WanPipeline
    from diffusers.utils import export_to_video
    from PIL import Image

    name = MODELS[model]
    img = Image.open(io.BytesIO(still)).convert("RGB")
    W, H = (1280, 704) if model == "5b" else (1280, 720)
    # crop the still to the clip's shape, then size it
    r = W / H
    w, h = img.size
    if w / h > r:
        nw = int(h * r); img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / r); img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize((W, H), Image.LANCZOS)
    Pipe = WanPipeline if model == "5b" else WanImageToVideoPipeline
    pipe = Pipe.from_pretrained(name, torch_dtype=torch.bfloat16).to("cuda")
    g = torch.Generator("cuda").manual_seed(seed)
    out = pipe(image=img, prompt=prompt, negative_prompt=NEG, height=H, width=W, num_frames=frames,
               guidance_scale=5.0, num_inference_steps=40 if model == "14b" else 50, generator=g).frames[0]
    cache.commit()
    path = "/tmp/clip.mp4"
    export_to_video(out, path, fps=24 if model == "5b" else 16)
    return open(path, "rb").read()


@app.local_entrypoint()
def main(still: str, prompt: str, out: str, frames: int = 81, seed: int = 1, model: str = "5b"):
    import os
    data = generate.remote(open(still, "rb").read(), prompt, frames, seed, model)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "wb").write(data)
    print("saved", out, len(data), "bytes")
