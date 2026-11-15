import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';

// Exercise the actual module shipped in the page, not a second implementation.
export function runViewportTests(html) {
  const source = html.match(/<script type="module" id="lightcraft-viewport-module">([\s\S]*?)<\/script>/)?.[1];
  assert.ok(source, 'the visible-viewport module must be present');
  const listeners = new Map();
  const frames = [];
  let writes = 0;
  const style = new Proxy({}, { set(target, key, value) { writes++; target[key] = value; return true; } });
  const viewport = {
    width: 402, height: 700, offsetLeft: 0, offsetTop: 0, scale: 1,
    addEventListener(name, callback) { listeners.set(`visual:${name}`, callback); },
  };
  const context = vm.createContext({
    window: { visualViewport: viewport, addEventListener(name, callback) { listeners.set(`window:${name}`, callback); } },
    document: { getElementById(id) { assert.equal(id, 'lightcraft_viewport'); return { style }; } },
    requestAnimationFrame(callback) { frames.push(callback); return frames.length; },
  });
  vm.runInContext(source.replace('export function', 'function'), context);
  const box = context.viewportBox;
  const plain = value => JSON.parse(JSON.stringify(value));
  const fire = name => { assert.ok(listeners.has(name), name); listeners.get(name)(); };
  const flush = () => { while (frames.length) frames.shift()(); };

  assert.deepEqual(plain(box(viewport)), { left: 0, top: 0, width: 402, height: 700 });
  assert.equal(style.width, '402px');
  assert.equal(style.height, '700px');
  const initialWrites = writes;
  fire('visual:resize'); fire('visual:scroll'); fire('window:orientationchange');
  assert.equal(frames.length, 1, 'viewport events must coalesce into one frame');
  flush();
  assert.equal(writes, initialWrites, 'unchanged geometry must not cause a resize loop');

  Object.assign(viewport, { height: 320, offsetTop: 40 });
  fire('visual:resize'); flush();
  assert.equal(style.height, '320px', 'keyboard reduces the usable area');
  assert.equal(style.top, '40px');
  Object.assign(viewport, { width: 874, height: 330, offsetTop: 0 });
  fire('window:orientationchange'); flush();
  assert.equal(style.width, '874px');
  assert.equal(style.height, '330px');

  Object.assign(viewport, { scale: 2, width: 437, height: 165 });
  fire('visual:resize'); flush();
  assert.equal(style.width, '874px', 'pinch magnification must not shrink and reflow the app');
  assert.equal(box(viewport), null);
  Object.assign(viewport, { scale: 1, width: 402, height: 700 });
  fire('window:pageshow'); flush();
  assert.equal(style.width, '402px');
  assert.equal(style.height, '700px');

  for (const value of [undefined, { ...viewport, width: 0 }, { ...viewport, height: NaN }, { ...viewport, offsetTop: Infinity }]) {
    assert.equal(box(value), null, 'invalid transitional geometry must retain the current layout');
  }
  assert.equal(box({ ...viewport, offsetTop: -12 }).top, 0);
  assert.match(html, /viewport-fit=cover/);
  for (const edge of ['top', 'right', 'bottom', 'left']) assert.ok(html.includes(`safe-area-inset-${edge}`));
  assert.match(html, /height: 100svh; height: 100dvh/);
  assert.doesNotMatch(html, /user-scalable\s*=\s*no|maximum-scale\s*=\s*1|transform\s*:\s*scale\(/);
  assert.doesNotMatch(source, /canvas\.(?:width|height)\s*=/, 'eframe owns canvas backing-store dimensions');
  return 'Viewport checks passed: portrait, keyboard, rotation, zoom, recovery, coalescing, invalid metrics and safe areas.';
}

if (typeof process !== 'undefined' && process.argv[1]?.endsWith('test_viewport.mjs')) {
  const path = process.argv[2];
  assert.ok(path, 'pass the patched apps/lightcraft-web/index.html path');
  console.log(runViewportTests(await readFile(path, 'utf8')));
}
