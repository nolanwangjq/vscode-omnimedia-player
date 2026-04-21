# Changelog

All notable changes to **Omnimedia Player** are documented here.

---

## [0.3.0] — 2026-04-21

### Added
- **Zoom & Pan** — scroll the mouse wheel over the video to zoom in or out (1×–4×, steps of 0.1). A zoom button in the controls bar cycles through preset levels: 1× → 1.5× → 2× → 3×. When zoomed in, drag the video to pan. A 3 px movement threshold prevents accidental pan during a click.
- **Configurable external player** — new setting `videoPreview.externalPlayerPath` (machine-scoped). Set it to the path of any video player (e.g. `C:\Program Files\PotPlayer\PotPlayerMini64.exe`) and "Open in External Player" will launch it directly. Falls back to the system default when the setting is empty or in a remote session.
- **Save Video button** — new action-bar button that opens a native save dialog defaulting to the user's `Downloads` folder, then saves a copy of the video via `workspace.fs.copy` (works in local and remote sessions alike).

### Changed
- "Open in External Player" no longer uses `execFile` in remote (SSH / WSL / Codespaces) sessions to avoid running a local GUI app on the remote machine; it falls back to `vscode.env.openExternal` in those cases.

---

## [0.2.0]

### Fixed
- **Codec detection** — replaced extension-name guessing with actual ffprobe detection. Only H.264 + yuv420p in `.mp4` / `.mov` / `.m4v` plays natively; all other codecs (H.265, MPEG-4, VP8/VP9, MJPEG, etc.) are automatically transcoded to H.264/yuv420p.
- **No-audio video handling** — videos without an audio track no longer show a spurious "Extracting audio…" bar. Audio extraction is skipped when ffprobe confirms no audio stream exists.
- **Video not loading** — replaced local HTTP server (`http://127.0.0.1`) with `webview.asWebviewUri()`. Electron treats `http://` as mixed content in webviews and blocks it unconditionally.
- **Transcoded output still unplayable** — transcode command was missing `-pix_fmt yuv420p`; videos with non-standard pixel formats (e.g. `yuv444p`) remained unplayable after transcoding.
- **Error routing** — transcode failures and audio-extraction failures previously shared a single error handler, causing transcode errors to be misreported as audio failures.
- **Message race condition** — if a transcoded file was already cached the `video_src` message could arrive before the webview finished initialising. Added a `postWhenReady` queue that buffers messages until the webview signals readiness.
- **ffmpeg process leak** — closing the preview panel while transcoding was in progress left an orphaned ffmpeg process running. The process is now killed on panel dispose.

### Added
- **Real-time transcode progress bar** — replaced blocking `execFile` with `spawn` + `-progress pipe:1`, showing live progress ("Transcoding video for playback... 42%") during ffmpeg transcoding.

---

## [0.1.0]

- A copy of https://github.com/ChetSocio/vscode-video-preview 
- Support for MP4, WebM, MOV, MKV, AVI, M4V.
- Audio playback via ffmpeg extraction.
- Playback controls: play/pause, seek, volume, mute, speed (0.5×–2×), 10-second skip, Picture-in-Picture, fullscreen.
- Open in external player, copy file path.
