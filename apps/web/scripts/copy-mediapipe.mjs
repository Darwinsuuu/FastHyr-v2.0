// Copies MediaPipe's WebAssembly files from node_modules into public/mediapipe/ (INTV-003), so
// the device check's face detection loads from our own host: nothing is fetched from a third
// party and no camera frame leaves the browser. The copies are git-ignored; `dev` and `build`
// run this first. The face model (blaze_face_short_range.tflite) is committed next to them.

import { copyFileSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const target = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "mediapipe");

// What FilesetResolver.forVisionTasks("/mediapipe") asks for: the SIMD build, or the no-SIMD
// one on browsers without WebAssembly SIMD.
const FILES = [
  "vision_wasm_internal.js",
  "vision_wasm_internal.wasm",
  "vision_wasm_nosimd_internal.js",
  "vision_wasm_nosimd_internal.wasm",
];

mkdirSync(target, { recursive: true });
for (const file of FILES) {
  const source = require.resolve(`@mediapipe/tasks-vision/${file}`);
  const destination = join(target, file);
  let fresh = false;
  try {
    const [from, to] = [statSync(source), statSync(destination)];
    fresh = from.size === to.size && from.mtimeMs <= to.mtimeMs;
  } catch {
    // Not copied yet.
  }
  if (!fresh) copyFileSync(source, destination);
}
