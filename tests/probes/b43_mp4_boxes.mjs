#!/usr/bin/env node
/**
 * b43_mp4_boxes.mjs — top-level ISO-BMFF (MP4) box walker.
 *
 * WHY THIS EXISTS: B4.3 established that `Research_Demo_Video.mp4` was not
 * faststart by parsing its container boxes directly, at a time when no ffprobe
 * was installed on the machine. That parse was ad-hoc and left no artifact, so
 * the finding could not be re-checked by anyone else (CLAUDE.md Rule 20). This
 * is that method, committed.
 *
 * It answers three questions ffprobe answers only indirectly:
 *   1. Is `moov` BEFORE `mdat`?  -> progressive playback starts without
 *      buffering the whole file. This is what `-movflags +faststart` buys, and
 *      it is a property of BOX ORDER, not of any stream field.
 *   2. Is there an audio track?  -> counted from `trak`/`hdlr` handler types.
 *   3. What is the byte budget?  -> per-box sizes.
 *
 * Usage:
 *   node tests/probes/b43_mp4_boxes.mjs <file.mp4> [--json <out.json>]
 *
 * Exit code is 0 when the file is faststart AND has no audio track, 1
 * otherwise, so it can be used as an assertion in a ship gate.
 */
import { readFileSync, writeFileSync } from 'node:fs';

const args = process.argv.slice(2);
const file = args[0];
if (!file) {
  console.error('usage: node b43_mp4_boxes.mjs <file.mp4> [--json <out.json>]');
  process.exit(2);
}
const jsonIdx = args.indexOf('--json');
const jsonOut = jsonIdx >= 0 ? args[jsonIdx + 1] : null;

const buf = readFileSync(file);

/** Walk the top-level box list only (no recursion into container payloads). */
function topLevelBoxes(b) {
  const out = [];
  let off = 0;
  while (off + 8 <= b.length) {
    let size = b.readUInt32BE(off);
    const type = b.toString('latin1', off + 4, off + 8);
    let header = 8;
    if (size === 1) {
      // 64-bit largesize in the 8 bytes following the type.
      if (off + 16 > b.length) break;
      size = Number(b.readBigUInt64BE(off + 8));
      header = 16;
    } else if (size === 0) {
      // Box extends to end of file.
      size = b.length - off;
    }
    if (size < header || off + size > b.length) {
      out.push({ type, offset: off, size, truncated: true });
      break;
    }
    out.push({ type, offset: off, size });
    off += size;
  }
  return out;
}

/**
 * Count tracks by handler type. `hdlr` boxes are nested inside
 * moov>trak>mdia, so scan the moov payload for the 4CC rather than
 * implementing full recursion — the handler types are unambiguous.
 */
function handlerTypes(b, moov) {
  if (!moov) return [];
  const slice = b.subarray(moov.offset, moov.offset + moov.size);
  const found = [];
  for (let i = 0; i + 12 <= slice.length; i++) {
    if (slice.toString('latin1', i, i + 4) === 'hdlr') {
      // hdlr: 4 version/flags + 4 pre_defined + 4 handler_type
      const h = slice.toString('latin1', i + 12, i + 16);
      found.push(h);
    }
  }
  return found;
}

const boxes = topLevelBoxes(buf);
const order = boxes.map((x) => x.type);
const moov = boxes.find((x) => x.type === 'moov');
const mdat = boxes.find((x) => x.type === 'mdat');
const handlers = handlerTypes(buf, moov);

const moovIdx = order.indexOf('moov');
const mdatIdx = order.indexOf('mdat');
const faststart = moovIdx >= 0 && mdatIdx >= 0 && moovIdx < mdatIdx;
const audioTracks = handlers.filter((h) => h === 'soun').length;
const videoTracks = handlers.filter((h) => h === 'vide').length;

const result = {
  file,
  bytes: buf.length,
  topLevelOrder: order,
  boxes: boxes.map(({ type, offset, size }) => ({ type, offset, size })),
  moovOffset: moov ? moov.offset : null,
  mdatOffset: mdat ? mdat.offset : null,
  faststart,
  handlers,
  videoTracks,
  audioTracks,
};

const lines = [
  `file:        ${file}`,
  `bytes:       ${buf.length.toLocaleString('en-US')} (${(buf.length / 1048576).toFixed(2)} MB)`,
  `box order:   ${order.join(' -> ')}`,
  ...boxes.map(
    (x) =>
      `  ${x.type.padEnd(6)} offset ${String(x.offset).padStart(10)}  size ${String(
        x.size
      ).padStart(10)}`
  ),
  `handlers:    ${handlers.join(', ') || '(none)'}`,
  `video trks:  ${videoTracks}`,
  `audio trks:  ${audioTracks}`,
  `FASTSTART:   ${faststart ? 'YES — moov before mdat' : 'NO — moov is NOT before mdat'}`,
];
console.log(lines.join('\n'));

if (jsonOut) {
  writeFileSync(jsonOut, JSON.stringify(result, null, 2) + '\n');
  console.log(`\nwrote ${jsonOut}`);
}

process.exit(faststart && audioTracks === 0 ? 0 : 1);
