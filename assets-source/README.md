# assets-source/ — source masters, NOT shipped

Files here are **inputs to a build step**, kept in the repo so the shipped
asset can be re-derived, but deliberately **outside `public/`**.

## Why this directory exists

Next.js copies `public/` into the static export **wholesale** — every byte,
referenced or not. At B4.3 R4 that meant the export carried **13.2 MB of dead
media**: the 11.78 MB screen-recording master and the 859 KB B4.2 PNG, neither
of which any page referenced after the panel switched to the encoded video.
Moving them here removes them from `out/` without deleting the originals.

**The rule: if a file is not fetched by a URL at runtime, it does not belong in
`public/`.**

## Current contents

| file | what it is | what was derived from it |
|---|---|---|
| `media/Research_Demo_Video.mp4` | the founder's original screen recording — 1662×938, 39.33 s, **has an audio track**, not faststart, 11.78 MB | `public/media/research-demo.mp4` and `public/media/research-demo-poster.jpg` |
| `media/demo-research-20260814.png` | the B4.2 static demo still, 1975×1114, 859 KB | superseded by the video; retained as the record of what B4.2 shipped |

## Re-deriving the shipped video

The cut is two segments joined, 1× throughout (no speed ramp — speeding the
loading phase would misrepresent real product latency). Segment 1 ends at
31.00 s specifically because the on-screen `Query time: 16.06s` enters between
31.00 and 31.20, and that performance claim is deliberately excluded.

```bash
ffmpeg -y -i assets-source/media/Research_Demo_Video.mp4 \
  -filter_complex "[0:v]trim=start=21.30:end=31.00,setpts=PTS-STARTPTS[a];\
[0:v]trim=start=35.10:end=38.60,setpts=PTS-STARTPTS[b];\
[a][b]concat=n=2:v=1:a=0[cc];[cc]scale=1440:-2[v]" \
  -map "[v]" -c:v libx264 -crf 21 -preset slow -an -pix_fmt yuv420p \
  -movflags +faststart public/media/research-demo.mp4

# Poster from the ORIGINAL, not from the encode — pulling a JPEG out of the
# h264 output compounds compression artifacts.
ffmpeg -y -ss 38.00 -i assets-source/media/Research_Demo_Video.mp4 \
  -frames:v 1 -vf scale=1440:-2 -q:v 5 public/media/research-demo-poster.jpg
```

Verify the result with the committed box walker, which checks the two things
`ffprobe` only answers indirectly — that `moov` precedes `mdat` (faststart) and
that no audio track survived:

```bash
node tests/probes/b43_mp4_boxes.mjs public/media/research-demo.mp4
```

It exits non-zero on failure, and reports `faststart NO` + 1 audio track when
pointed at the master — which is its negative control.
