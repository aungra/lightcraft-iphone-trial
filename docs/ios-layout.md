# iPhone layout revision r1

This is an unofficial modification of LightCraft v0.21.1. Runtime acceptance on a physical iPhone is separate from a successful build.

## Reproduced problem

The user reports that JPEG editing works on iPhone 16 Pro / iOS 26 Safari, but portrait menus and editing panels are clipped. Safari 27.0.1 on macOS, in its 402 × 874 responsive preview, also shows the original top-bar menu, search and buttons overlapping. A desktop responsive preview does not reproduce every iOS browser behavior.

The original desktop columns require more width than a phone provides. The canvas application is drawn by egui; CSS alone cannot rearrange its internal panels. The revision adds a width-driven compact workspace, a full-width drill-in menu, and a scrollable bottom editing panel. The desktop docking arrangement is retained when rotating or returning to a wide viewport.

## Reference decisions

- [Apple layout guidance](https://developer.apple.com/design/human-interface-guidelines/layout) and [WebKit safe-area guidance](https://webkit.org/blog/7929/designing-websites-for-iphone-x/): keep essential controls inside the safe area. Insets belong on the canvas container, not padding on the canvas itself.
- [WebKit viewport units](https://webkit.org/blog/12445/new-webkit-features-in-safari-15-4/): use dynamic viewport height with conservative CSS fallbacks for browser chrome changes.
- [VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport): track the visible rectangle for keyboard, orientation and viewport changes. Coalesce events into animation frames. Avoid relayout during pinch zoom, and do not disable user zoom.
- [Pinned eframe canvas observer](https://github.com/storytold/egui/blob/6d518fc799681571963842f95b55a6b68431b15a/crates/eframe/src/web/events.rs): leave backing-store pixel sizing to eframe. Host CSS controls the container rectangle.
- [Upstream mobile issue](https://github.com/storytold/lightcraft/issues/707): treat phone support as a separate acceptance target.
- [WebKit issue 300523](https://bugs.webkit.org/show_bug.cgi?id=300523): some iOS 26 releases report stale viewport offsets around keyboard dismissal. Do not guess a fixed pixel correction or force page scrolling. Validate the actual iPhone minor version and browser behavior.

## Verification boundaries

The source patch contains headless egui checks for narrow portrait, landscape and keyboard-height layouts, touch-target geometry, drill-in menus, dialogs, photo controls and preservation of the desktop dock. `tests/test_viewport.mjs` executes the actual inline viewport module with deterministic event/geometry mocks. The complete upstream CI gate and WASM compilation are required before publication. These checks do not simulate the iOS keyboard, touch input, browser bars or memory pressure.

After publishing, check portrait and landscape on Safari: import, menu navigation, exposure and white balance, crop, export dialog, panel scrolling, rotation, keyboard dismissal and page reopen. On a physical iPhone, verify that essential buttons remain visible as Safari's bars expand and retract. Use copies and retain a library backup.

A separate one-line clock correction replaces `std::time::Instant` with the engine's existing `web_time::Instant` in RAW hot-pixel removal. The former panics on `wasm32-unknown-unknown`. A synthetic DNG regression preserves hot-pixel correction. Successful JPEG editing or this native regression does not establish GR IIIx / Nikon RAW runtime support; replay and inspect those formats independently.

## Distribution

Publish the reviewed modified build at `/iphone-r1/`, retaining the exact official `/v0.21.1/` files. Both paths share this site's browser-local library. No storage schema, RAW engine, upload service or synchronization service is added. Preserve licenses and notices; the web build does not embed the native ArtCraft logo. Plain-text attribution identifies the upstream authors without suggesting endorsement.
