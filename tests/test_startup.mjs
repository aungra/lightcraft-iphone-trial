import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';

export async function runStartupTests(html) {
  const extract = id => {
    const source = html.match(new RegExp(`<script type="module" id="${id}">([\\s\\S]*?)<\\/script>`))?.[1];
    assert.ok(source, `${id} missing`);
    return source;
  };
  const startup = extract('lightcraft-startup-module');
  // Test real shipped functions without executing the application boot.
  const functions = startup.slice(startup.indexOf('    // Japanese'), startup.indexOf('    (async () =>'))
    .replaceAll('export ', '');
  const context = vm.createContext({ URLSearchParams, Uint8Array });
  vm.runInContext(functions, context);
  let calls = 0;
  const fetcher = async () => { calls++; return { ok: true, arrayBuffer: async () => new Uint8Array([1, 2]).buffer }; };
  const noFont = await context.loadChineseFont('?workers=1&font=ja', fetcher);
  assert.equal(noFont.length, 0);
  assert.equal(calls, 0, 'Japanese startup must not fetch or wait for the Chinese font');
  for (const query of ['', '?font=zh', '?font=', '?font=unexpected']) {
    assert.equal(context.needsChineseFont(query), true, 'default and unknown modes preserve Chinese glyphs');
    assert.equal((await context.loadChineseFont(query, fetcher)).length, 2);
  }
  assert.equal((await context.loadChineseFont('', async () => { throw Error('offline'); })).length, 0);
  assert.equal((await context.loadChineseFont('', async () => ({ ok: false }))).length, 0);
  assert.match(startup, /loadChineseFont\(location.search, fetch\)/, 'boot must use tested policy');
  assert.match(startup, /start\(font\)/, 'selected font reaches the app');
  const perf = extract('lightcraft-performance-module');
  vm.runInContext(perf.slice(0, perf.indexOf('    const timings =')).replaceAll('export ', ''), context);
  const timings = context.createTimings();
  for (let i = 0; i < 100; i++) timings.add({ stage: 'import_hash', duration_ms: i + .2, bytes: 10, filename: 'private.jpg' });
  const snap = timings.snapshot();
  assert.equal(snap.length, 40, 'diagnostic history must remain bounded');
  assert.equal(snap[0].duration_ms, 60);
  assert.equal('filename' in snap[0], false, 'unknown fields must not retain private photo metadata');
  snap[0].duration_ms = 999;
  assert.equal(timings.snapshot()[0].duration_ms, 60, 'readers cannot alter recorded timings');
  for (const value of [null, {}, { stage: 'private.jpg', duration_ms: 1, bytes: 0 },
    { stage: 'import_hash', duration_ms: Infinity, bytes: 0 }, { stage: 'import_hash', duration_ms: -1, bytes: 0 }]) timings.add(value);
  assert.equal(timings.snapshot().length, 40);
  assert.equal(timings.snapshot().at(-1).duration_ms, 99);
  console.log('Startup/font policy and bounded privacy-preserving diagnostic checks passed.');
}
if (typeof process !== "undefined" && process.argv[2]) await runStartupTests(await readFile(process.argv[2], 'utf8'));
