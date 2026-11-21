# When Earth Shakes: handoff (read this first in a new chat)

A trailer and, later, a story RPG from the owner's Midjourney stills. Audience: young adults, but clean enough
for a 5-year-old. The dragon ("the Beast") is black, intense but never in your face; in the trailer it is NOT shown.

## Where things are
- `story.md`: the owner's story, beat by beat, with the stills for each beat.
- `stills/`, `stills.json`: the owner's stills and a catalogue.
- `bible/`: the canon. `canon.md` (the owner's picks), `style.md` (painted American realism, in the manner of
  Bo Bartlett, described in words), `cards/` (character and prop sheets: bookkeeper, lady, boy, helmet, props).
  Canon helmet = the FIRST grey one (pale grey-tan steel, wide letterbox slot, dark cloth hood); worn by the
  Bookkeeper (face from `cards/bookkeeper.jpg`). The Lady's face = the leftmost front view on her card.
  Open: which sword (slim curved, or straight old).
- `bible/picker/`: the canon picker page (published artifact "Character canon picker"; choices in its db).
- `trailer/`: `edit.json` (the cut), `build.py` (renders it), `score.py` (music in code), `voice/` (Job 41 lines,
  designed Gemini voice `voice_fbzr3xumfwod`), `sfx/` (public-domain fire and explosions, credited).
  Rough cut 8 was rejected by the owner: jumping between stills does not tell the story and is dull without motion.
- `tools/make-image.py` (Gemini image, about 15 cents), `tools/make-voice.py`, `tools/animate_modal.py` (Wan 2.2 on Modal).

## Next
1. Animation test: two stills (12 smoke column, 34 running at the fire) on Modal: `modal run tools/animate_modal.py ...`.
   Needs MODAL_TOKEN_ID / MODAL_TOKEN_SECRET (environment variables on the cloud environment; a session started
   after they were saved sees them). Free alternative: the Hugging Face Space r3gm/wan2-2-fp8da-aoti-preview (about 3 clips a day).
2. Then: the trailer re-cut in story order, 12 to 14 animated shots of 3 to 5 s, the mother's and the Lady's lines as voice.

## Money
Before any paid call, say the cost and wait for a yes. Spent so far: voice about 10 cents; cards about $2.55.
Google's prepaid credit ran out on Nov 21 (top up at ai.studio/projects).

## Rules from the owner
- Fewer faces, more powerful scenery; music under everything; real sound effects, not synthetic clicks.
- Slender, realistic proportions; strictly 1930s clothes (boy's scenes about 1910).
- Before and after stills for every visual change; the owner's eyes and ears decide.
