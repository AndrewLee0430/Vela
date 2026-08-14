# assets-source/ — source masters, NOT shipped

Files here are **inputs to a build step**, kept in the repo so the shipped
asset can be re-derived, but deliberately **outside `public/`**.

## Why this directory exists

Next.js copies `public/` into the static export **wholesale** — every byte,
referenced or not. At B4.3 R4 that meant the export carried **13.2 MB of dead
media**: the screen-recording master and the 859 KB B4.2 PNG, neither of which
any page referenced after the panel switched to the encoded video. Moving them
here removes them from `out/` without deleting the originals.

**The rule: if a file is not fetched by a URL at runtime, it does not belong in
`public/`.** The panel probe (`tests/probes/b41d_panel_smoke.mjs`) asserts that
`out/media` contains exactly the two shipped files, so a master landing back in
`public/` fails the build gate rather than shipping silently.

⚠️ **A re-record usually arrives in `public/media/` with the master's filename.**
That is how the founder's screen recorder saves it. Move it here before doing
anything else — and note that the move OVERWRITES the previous take, since both
carry the same name.

## Current contents

| file | what it is | what was derived from it |
|---|---|---|
| `media/Research_Demo_Video.mp4` | **take 2** (2026-08-14, re-recorded after the B4.5 answer-pane scroll fix) — **1646×946, 51.667 s**, 30 fps, **has an audio track**, not faststart, 13,209,358 B (12.60 MB) | `public/media/research-demo.mp4` and `public/media/research-demo-poster.jpg` |
| `media/demo-research-20260814.png` | the B4.2 static demo still, 1975×1114, 859 KB | superseded by the video; retained as the record of what B4.2 shipped |

### Take history

- **take 1** — 1662×938, 39.333 s, 12,353,959 B. **Overwritten by take 2** (same
  filename). Recoverable from commit **`2fa9dd9`**:
  `git show 2fa9dd9:assets-source/media/Research_Demo_Video.mp4 > take1.mp4`.
  Its cut was **two segments** (`21.30–31.00` + `35.10–38.60`) joined with
  `concat`, because the on-screen `Query time: 16.06s` occupied ~31.1–34.9 s and
  a **visible performance claim must not ship on a public page**. Take 2 needs
  no join: the answer pane grows to its `max-h-[500px]` and pushes the composer —
  and the query-time line beneath it — below the recorded frame before the
  stream completes, so the timer never enters shot. **Verify that per take; do
  not assume it.**

## Re-deriving the shipped video (take 2)

Single segment, 1× throughout. **No speed ramp** — speeding the loading phase
would distort time and misrepresent real product latency; selecting *which*
segment to show does not. The window opens ~1 s before the first tokens, on the
"Checking & ranking sources" state, so the loop reads reset → work → result, and
holds ~4.5 s on the finished answer so the Summary card can actually be read.

```bash
FFMPEG=".../ffmpeg-9.0-full_build/bin/ffmpeg.exe"   # not on PATH; use absolute

"$FFMPEG" -y -i assets-source/media/Research_Demo_Video.mp4 \
  -filter_complex "[0:v]trim=start=33.20:end=47.00,setpts=PTS-STARTPTS[a];\
[a]scale=1440:-2[v]" \
  -map "[v]" -c:v libx264 -crf 21 -preset slow -an -pix_fmt yuv420p \
  -movflags +faststart public/media/research-demo.mp4

# Poster from the ORIGINAL, not from the encode — pulling a JPEG out of the
# h264 output compounds compression artifacts. t=47.00 is the cut's final
# frame, in the post-scroll state where the Summary card sits at the top of
# the pane (the B4.5 fix), which is the better first impression.
"$FFMPEG" -y -ss 47.00 -i assets-source/media/Research_Demo_Video.mp4 \
  -frames:v 1 -vf scale=1440:-2 -q:v 5 public/media/research-demo-poster.jpg
```

Result: **1440×828, 13.800 s, 414 frames, 2,325,186 B (2.22 MB)**; poster
**1440×828, 110,304 B**.

⚠️ **The output dimensions move with every re-record** — take 1 gave 1440×812,
take 2 gives 1440×828, because the two recordings have different window sizes.
Three places carry that pair and must be re-read from `ffprobe`, never carried
over, or the frame is squashed silently:

- `components/LandingSections.tsx` — the `<video>` `width` / `height`
- `components/LandingSections.tsx` — the explicit `style={{ aspectRatio }}`
- `tests/probes/b41d_panel_smoke.mjs` — the assertions that pin all three

## Verifying the result

```bash
node tests/probes/b43_mp4_boxes.mjs public/media/research-demo.mp4
```

Checks the two things `ffprobe` only answers indirectly — that `moov` precedes
`mdat` (faststart) and that no audio track survived. Exits non-zero on failure,
and reports `faststart NO` + 1 audio track when pointed at the master, which is
its negative control.
