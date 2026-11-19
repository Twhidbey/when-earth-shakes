# Trailer plan: "When Earth Shakes" (DRAFT 1)

Not in story order: a build from quiet to fury. About 75 to 90 seconds.
Voiceover: Job 41 (King James Version, public domain), read slowly by a deep voice,
treated as an old radio broadcast (thin, warm, crackle, a little hum), the way the
Revelation reading opens Johnny Cash's "The Man Comes Around". Our own reading: no Cash audio.

Verse text checked against the KJV (npm `bible-kjv`).

## Act 1: the hush (0:00 to 0:25). Radio crackle, wind, a far rumble. No music yet.

| Time | Shot | Sound / voice |
|---|---|---|
| 0:00 | black | radio dial tuning, static settles |
| 0:03 | 05-hand-wheat (slow drift right) | V.O. "Canst thou draw out leviathan with an hook?" (41:1) |
| 0:09 | 47-aerial-fields (slow push down) | wind; a deep rumble under it |
| 0:13 | 11-strange_sounds2 (push in on the red box) | a needle scratching, ticking faster |
| 0:18 | 04-boy-fire-field (very slow push) | V.O. "Upon earth there is not his like, who is made without fear." (41:33) |
| 0:24 | cut to black | the rumble stops dead |

## Act 2: the sign (0:25 to 0:50). A low drone starts, a slow heartbeat drum.

| Time | Shot | Sound / voice |
|---|---|---|
| 0:25 | 12-plume_of_smoke2 | a crash, far off; the ground thuds |
| 0:30 | 15-town-watches-smoke | V.O. "When he raiseth up himself, the mighty are afraid." (41:25) |
| 0:35 | 13-dragon_emerging3 (slow push toward the black mass) | the drone swells |
| 0:40 | 27-dragon-scales (slide across) | V.O. "His scales are his pride, shut up together as with a close seal." (41:15) |
| 0:45 | 28-dragon-eye (pupil narrows) | one deep breath, close |
| 0:48 | 14-found_in_burning_field (from above) | fire crackle |

## Act 3: the rise (0:50 to 1:10). Music builds; cuts get faster, on the beat.

| Time | Shot | Sound / voice |
|---|---|---|
| 0:50 | 20-I_will_face4 | V.O. "Lay thine hand upon him, remember the battle." (41:8) |
| 0:54 | 22-helmet3 (the slot, eyes) | steel visor clank |
| 0:56 | 23-gun | two shells loaded, the breech snaps shut |
| 0:58 | 25-helmet-field-a | the beat drops in |
| 1:00 | 34-running_from_fire | V.O. "Out of his mouth go burning lamps, and sparks of fire leap out." (41:19) |
| 1:04 | 35-running_in_fire | roar of fire |
| 1:06 | 31-dragon-shooter | a shotgun blast; the wings beat |
| 1:08 | 41-roar (very brief) | the Beast's roar |

## Act 4: the hold (1:10 to 1:25). Everything cuts out.

| Time | Shot | Sound / voice |
|---|---|---|
| 1:10 | 36b-waking_up | silence; water dripping |
| 1:13 | 37-sword (light runs along the blade) | V.O. "The sword of him that layeth at him cannot hold." (41:26) |
| 1:18 | 40-face_to_face_again (slow push) | one low note; the wings unfold |
| 1:23 | black | |

## Title (1:25 to 1:32)

| Time | Shot | Sound / voice |
|---|---|---|
| 1:25 | title over 29-fire-smoke-abstract: WHEN EARTH SHAKES | V.O. "His heart is as firm as a stone." (41:24) |
| 1:30 | black; radio crackle fades | |

Why these verses: 41:26 says no sword can hold against him, and the sword is exactly what wins;
41:24 ("his heart is as firm as a stone") foretells the Beast turning to stone as it falls.

Spare verses: 41:14 "Who can open the doors of his face? his teeth are terrible round about."
41:20 "Out of his nostrils goeth smoke, as out of a seething pot or caldron."
41:21 "His breath kindleth coals, and a flame goeth out of his mouth."
41:18 "his eyes are like the eyelids of the morning."

## To make it
- Motion: free first (slow push-ins, parallax by depth map); a few shots animated by AI later (eye, wings, fire, smoke).
- Voice: Gemini TTS in a deep designed voice (about 1 cent a line), or the owner's own recording; then an
  old-radio treatment in ffmpeg (band-pass about 300 to 3400 Hz, light saturation, crackle and hum), free.
- Music: a licensed track (dark Americana, slow build) or a drone, heartbeat drum and hits made in code.
- Assembly: `trailer/edit.json` (shots, times, moves, sound cues) built by an ffmpeg script.
