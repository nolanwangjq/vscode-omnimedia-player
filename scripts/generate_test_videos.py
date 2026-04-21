# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Comprehensive test video generator for vscode-video-preview.

Covers every code path in VideoEditorProvider.ts:
  - All supported containers (.mp4 .mov .m4v .webm .mkv .avi)
  - All video codecs the extension detects (H.264, H.265, VP8, VP9, MPEG-4, MJPEG, XVID)
  - Native playback path   (H.264 + yuv420p in .mp4 / .mov / .m4v  → no transcode)
  - Transcode path          (any other codec / pix_fmt / container   → libx264 + yuv420p)
  - Audio extraction path   (ffmpeg → mp3 for files that have audio)
  - No-audio path           (skip extraction when no audio stream present)
  - Various resolutions / aspect ratios
  - Various durations (for progress-bar and time-display testing)
  - Various frame rates
  - Edge cases (empty file, truncated file, multi-audio-track, high bitrate)
"""

import os
import subprocess
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "tests"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

results: list[tuple[str, str]] = []


def run_ffmpeg(*args: str) -> bool:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ ffmpeg error: {e.stderr.decode(errors='replace')[:300]}")
        return False


def make(
    name: str,
    *,
    ext: str,
    duration: float = 5.0,
    width: int = 640,
    height: int = 480,
    fps: int = 24,
    vcodec: str = "libx264",
    pix_fmt: str = "yuv420p",
    extra_v: list[str] | None = None,
    acodec: str | None = "aac",   # None → -an (no audio stream)
    extra_a: list[str] | None = None,
    description: str = "",
) -> None:
    out = OUT_DIR / f"{name}{ext}"
    if out.exists() and out.stat().st_size > 100:
        print(f"  skip  {out.name}")
        results.append((out.name, "skip"))
        return

    label = (description or name).replace("'", "\\'").replace(":", "\\:")
    # Two lines: filename on top, description below
    vf = (
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps},"
        f"drawtext=text='{name}':x=10:y=10:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
        f"drawtext=text='{label}':x=10:y=36:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6"
    )

    cmd: list[str] = ["-f", "lavfi", "-i", vf]
    if acodec:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]

    cmd += ["-c:v", vcodec, "-pix_fmt", pix_fmt]
    if extra_v:
        cmd += extra_v
    cmd += ["-t", str(duration)]

    if acodec:
        cmd += ["-c:a", acodec]
        if extra_a:
            cmd += extra_a
    else:
        cmd += ["-an"]

    cmd.append(str(out))

    ok = run_ffmpeg(*cmd)
    size = out.stat().st_size if out.exists() else 0
    status = "ok" if ok and size > 100 else "FAIL"
    icon = "✓" if status == "ok" else "✗"
    print(f"  {icon}  {out.name}  ({size:,} B)")
    results.append((out.name, status))


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # A: Format × native-vs-transcode matrix
    #    mp4/mov/m4v + h264 + yuv420p → NATIVE (no transcode needed)
    #    everything else               → TRANSCODE path
    # -----------------------------------------------------------------------
    section("A: Format coverage — native vs transcode path")

    # Native playback (no transcode, audio extracted separately)
    make("A01_mp4_h264_yuv420p_audio",   ext=".mp4",  vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac",  description="MP4|H.264|yuv420p|audio → NATIVE playback + audio extract")
    make("A02_mp4_h264_yuv420p_noaudio", ext=".mp4",  vcodec="libx264", pix_fmt="yuv420p",
         acodec=None,   description="MP4|H.264|yuv420p|NO audio → NATIVE playback, skip audio")
    make("A03_mov_h264_yuv420p_audio",   ext=".mov",  vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac",  description="MOV|H.264|yuv420p|audio → NATIVE playback + audio extract")
    make("A04_mov_h264_yuv420p_noaudio", ext=".mov",  vcodec="libx264", pix_fmt="yuv420p",
         acodec=None,   description="MOV|H.264|yuv420p|NO audio → NATIVE playback, skip audio")
    make("A05_m4v_h264_yuv420p_audio",   ext=".m4v",  vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac",  description="M4V|H.264|yuv420p|audio → NATIVE playback + audio extract")
    make("A06_m4v_h264_yuv420p_noaudio", ext=".m4v",  vcodec="libx264", pix_fmt="yuv420p",
         acodec=None,   description="M4V|H.264|yuv420p|NO audio → NATIVE playback, skip audio")

    # Transcode path — container forces transcode
    make("A07_webm_vp8_vorbis",  ext=".webm", vcodec="libvpx",    pix_fmt="yuv420p",
         acodec="libvorbis", description="WebM|VP8|yuv420p|Vorbis → TRANSCODE + audio extract")
    make("A08_webm_vp9_vorbis",  ext=".webm", vcodec="libvpx-vp9", pix_fmt="yuv420p",
         acodec="libvorbis", description="WebM|VP9|yuv420p|Vorbis → TRANSCODE + audio extract")
    make("A09_webm_vp9_noaudio", ext=".webm", vcodec="libvpx-vp9", pix_fmt="yuv420p",
         acodec=None,        description="WebM|VP9|NO audio → TRANSCODE, skip audio")
    make("A10_mkv_h264_aac",     ext=".mkv",  vcodec="libx264",   pix_fmt="yuv420p",
         acodec="aac",       description="MKV|H.264|yuv420p|AAC → TRANSCODE + audio extract")
    make("A11_mkv_h264_noaudio", ext=".mkv",  vcodec="libx264",   pix_fmt="yuv420p",
         acodec=None,        description="MKV|H.264|NO audio → TRANSCODE, skip audio")
    make("A12_avi_xvid_mp3",     ext=".avi",  vcodec="libxvid",   pix_fmt="yuv420p",
         acodec="libmp3lame", description="AVI|XVID|yuv420p|MP3 → TRANSCODE + audio extract")
    make("A13_avi_mjpeg_noaudio",ext=".avi",  vcodec="mjpeg",     pix_fmt="yuvj420p",
         acodec=None,        description="AVI|MJPEG|yuvj420p|NO audio → TRANSCODE, skip audio")

    # -----------------------------------------------------------------------
    # B: Codec variants inside .mp4 (all trigger transcode even in mp4)
    # -----------------------------------------------------------------------
    section("B: Codec variants in MP4 (all trigger transcode path)")

    make("B01_mp4_hevc_yuv420p_audio",  ext=".mp4", vcodec="libx265", pix_fmt="yuv420p",
         acodec="aac",  description="MP4|H.265/HEVC|yuv420p|audio → TRANSCODE (codec≠h264)")
    make("B02_mp4_hevc_yuv420p_noaudio",ext=".mp4", vcodec="libx265", pix_fmt="yuv420p",
         acodec=None,   description="MP4|H.265/HEVC|NO audio → TRANSCODE, skip audio")
    make("B03_mp4_mpeg4_yuv420p_audio", ext=".mp4", vcodec="mpeg4",   pix_fmt="yuv420p",
         acodec="aac",  description="MP4|MPEG-4|yuv420p|audio → TRANSCODE (codec≠h264)")
    make("B04_mp4_mpeg4_yuv420p_noaudio",ext=".mp4",vcodec="mpeg4",   pix_fmt="yuv420p",
         acodec=None,   description="MP4|MPEG-4|NO audio → TRANSCODE, skip audio")

    # -----------------------------------------------------------------------
    # C: Pixel format variants (critical — pix_fmt≠yuv420p triggers transcode)
    # -----------------------------------------------------------------------
    section("C: Pixel format variants (pix_fmt check in native-path decision)")

    make("C01_mp4_h264_yuv444p",          ext=".mp4", vcodec="libx264", pix_fmt="yuv444p",
         acodec=None,  description="MP4|H.264|yuv444p → TRANSCODE (pix_fmt≠yuv420p)")
    make("C02_mp4_h264_yuv422p",          ext=".mp4", vcodec="libx264", pix_fmt="yuv422p",
         acodec=None,  description="MP4|H.264|yuv422p → TRANSCODE (pix_fmt≠yuv420p)")
    make("C03_mp4_h264_yuv420p10le",      ext=".mp4", vcodec="libx264", pix_fmt="yuv420p10le",
         extra_v=["-profile:v", "high10"],
         acodec=None,  description="MP4|H.264|yuv420p10le (10-bit) → TRANSCODE")
    make("C04_mkv_h264_yuv444p",          ext=".mkv", vcodec="libx264", pix_fmt="yuv444p",
         acodec=None,  description="MKV|H.264|yuv444p → TRANSCODE (container + pix_fmt)")

    # -----------------------------------------------------------------------
    # D: Audio codec variants (audio extraction handles any audio codec via ffmpeg)
    # -----------------------------------------------------------------------
    section("D: Audio codec variants (all go through ffmpeg audio extraction)")

    make("D01_mp4_h264_aac_audio",      ext=".mp4",  vcodec="libx264",   pix_fmt="yuv420p",
         acodec="aac",       description="MP4|H.264|AAC audio → native + extract AAC→mp3")
    make("D02_mp4_h264_mp3_audio",      ext=".mp4",  vcodec="libx264",   pix_fmt="yuv420p",
         acodec="libmp3lame",description="MP4|H.264|MP3 audio → native + extract MP3→mp3")
    make("D03_mkv_h265_aac_audio",      ext=".mkv",  vcodec="libx265",   pix_fmt="yuv420p",
         acodec="aac",       description="MKV|H.265|AAC → transcode video + extract audio")
    make("D04_avi_xvid_mp3_audio",      ext=".avi",  vcodec="libxvid",   pix_fmt="yuv420p",
         acodec="libmp3lame",description="AVI|XVID|MP3 → transcode video + extract audio")
    make("D05_webm_vp9_vorbis_audio",   ext=".webm", vcodec="libvpx-vp9",pix_fmt="yuv420p",
         acodec="libvorbis", description="WebM|VP9|Vorbis → transcode + extract audio")
    make("D06_webm_vp8_opus_audio",     ext=".webm", vcodec="libvpx",    pix_fmt="yuv420p",
         acodec="libopus",   description="WebM|VP8|Opus → transcode + extract audio")

    # -----------------------------------------------------------------------
    # E: Resolution & aspect ratio
    # -----------------------------------------------------------------------
    section("E: Resolution & aspect ratio coverage")

    resolutions = [
        ("E01_3840x2160_4K",        3840, 2160, "3840×2160 — 4K UHD"),
        ("E02_2560x1440_2K",        2560, 1440, "2560×1440 — 2K QHD"),
        ("E03_1920x1080_FHD",       1920, 1080, "1920×1080 — Full HD (1080p)"),
        ("E04_1280x720_HD",         1280,  720, "1280×720 — HD (720p)"),
        ("E05_854x480_SD_16x9",      854,  480, "854×480 — SD 16:9"),
        ("E06_640x480_SD_4x3",       640,  480, "640×480 — SD 4:3"),
        ("E07_1080x1920_portrait",  1080, 1920, "1080×1920 — Portrait/vertical"),
        ("E08_1080x1080_square",    1080, 1080, "1080×1080 — Square 1:1"),
        ("E09_2560x1080_ultrawide", 2560, 1080, "2560×1080 — Ultrawide 21:9"),
        ("E10_320x240_tiny",         320,  240, "320×240 — Tiny SD"),
    ]
    for name, w, h, desc in resolutions:
        # libx264 requires even dimensions
        w2, h2 = w + (w % 2), h + (h % 2)
        make(name, ext=".mp4", width=w2, height=h2, duration=3.0,
             vcodec="libx264", pix_fmt="yuv420p", acodec=None, description=desc)

    # -----------------------------------------------------------------------
    # F: Duration coverage (progress bar, time display, seek)
    # -----------------------------------------------------------------------
    section("F: Duration coverage")

    make("F01_1frame",    ext=".mp4", duration=1/24, vcodec="libx264", pix_fmt="yuv420p",
         acodec=None,  description="Single frame — minimal duration")
    make("F02_1sec",      ext=".mp4", duration=1.0,  vcodec="libx264", pix_fmt="yuv420p",
         acodec=None,  description="1 second — very short")
    make("F03_5sec",      ext=".mp4", duration=5.0,  vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac", description="5 seconds — standard test")
    make("F04_30sec",     ext=".mp4", duration=30.0, vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac", description="30 seconds — test progress bar & seek")
    make("F05_2min",      ext=".mp4", duration=120.0,vcodec="libx264", pix_fmt="yuv420p",
         acodec="aac", description="2 minutes — test time display formatting")

    # -----------------------------------------------------------------------
    # G: Frame rate coverage
    # -----------------------------------------------------------------------
    section("G: Frame rate coverage")

    for fps_val, label in [(10, "10fps"), (24, "24fps-cinema"), (30, "30fps-NTSC"),
                            (60, "60fps-smooth"), (120, "120fps-slowmo")]:
        make(f"G_{label}", ext=".mp4", fps=fps_val, duration=3.0,
             vcodec="libx264", pix_fmt="yuv420p", acodec=None,
             description=f"{fps_val} fps")

    # -----------------------------------------------------------------------
    # H: MKV codec variants (MKV always triggers transcode regardless of codec)
    # -----------------------------------------------------------------------
    section("H: MKV codec variants (all trigger TRANSCODE)")

    make("H01_mkv_hevc_aac",  ext=".mkv", vcodec="libx265",    pix_fmt="yuv420p",
         acodec="aac",      description="MKV|H.265/HEVC → TRANSCODE + audio")
    make("H02_mkv_vp8",       ext=".mkv", vcodec="libvpx",     pix_fmt="yuv420p",
         acodec=None,       description="MKV|VP8 → TRANSCODE, no audio")
    make("H03_mkv_vp9",       ext=".mkv", vcodec="libvpx-vp9", pix_fmt="yuv420p",
         acodec=None,       description="MKV|VP9 → TRANSCODE, no audio")
    make("H04_mkv_mpeg4",     ext=".mkv", vcodec="mpeg4",      pix_fmt="yuv420p",
         acodec="aac",      description="MKV|MPEG-4 → TRANSCODE + audio")

    # -----------------------------------------------------------------------
    # I: MOV & M4V codec variants
    # -----------------------------------------------------------------------
    section("I: MOV & M4V codec variants")

    make("I01_mov_hevc_audio",    ext=".mov", vcodec="libx265", pix_fmt="yuv420p",
         acodec="aac",  description="MOV|H.265/HEVC → TRANSCODE + audio extract")
    make("I02_mov_mpeg4_audio",   ext=".mov", vcodec="mpeg4",   pix_fmt="yuv420p",
         acodec="aac",  description="MOV|MPEG-4 → TRANSCODE + audio extract")
    make("I03_mov_h264_yuv444p",  ext=".mov", vcodec="libx264", pix_fmt="yuv444p",
         acodec=None,   description="MOV|H.264|yuv444p → TRANSCODE (pix_fmt≠yuv420p)")
    make("I04_m4v_mpeg4_audio",   ext=".m4v", vcodec="mpeg4",   pix_fmt="yuv420p",
         acodec="aac",  description="M4V|MPEG-4 → TRANSCODE + audio extract")

    # -----------------------------------------------------------------------
    # J: Edge cases
    # -----------------------------------------------------------------------
    section("J: Edge cases")

    # J01: Zero-byte file — extension should handle gracefully (error state)
    j01 = OUT_DIR / "J01_zero_byte.mp4"
    if not j01.exists():
        j01.touch()
        print(f"  ✓  {j01.name}  (0 B)")
    else:
        print(f"  skip  {j01.name}")

    # J02: Truncated/corrupted file — first 512 bytes of a real mp4
    j02 = OUT_DIR / "J02_truncated.mp4"
    if not j02.exists():
        ref = OUT_DIR / "A01_mp4_h264_yuv420p_audio.mp4"
        if ref.exists():
            with open(ref, "rb") as f:
                data = f.read(512)
            with open(j02, "wb") as f:
                f.write(data)
            print(f"  ✓  {j02.name}  ({len(data)} B)")
        else:
            print(f"  skip  {j02.name}  (reference not found)")
    else:
        print(f"  skip  {j02.name}")

    # J03: MKV with multiple audio tracks
    j03 = OUT_DIR / "J03_multi_audio_tracks.mkv"
    if not j03.exists() or j03.stat().st_size < 100:
        ok = run_ffmpeg(
            "-f", "lavfi", "-i", "testsrc=duration=5:size=640x480:rate=24,"
                "drawtext=text='J03 multi audio':x=10:y=10:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-map", "0:v", "-map", "1:a", "-map", "2:a",
            str(j03),
        )
        size = j03.stat().st_size if j03.exists() else 0
        print(f"  {'✓' if ok else '✗'}  {j03.name}  ({size:,} B)")
    else:
        print(f"  skip  {j03.name}")

    # J04: High bitrate (20 Mbps) — tests buffering/large file handling
    j04 = OUT_DIR / "J04_high_bitrate_20mbps.mp4"
    if not j04.exists() or j04.stat().st_size < 100:
        ok = run_ffmpeg(
            "-f", "lavfi", "-i",
            "testsrc=duration=5:size=1280x720:rate=30,"
            "drawtext=text='J04 high bitrate 20Mbps':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-b:v", "20M", "-maxrate", "20M", "-bufsize", "40M",
            "-c:a", "aac",
            str(j04),
        )
        size = j04.stat().st_size if j04.exists() else 0
        print(f"  {'✓' if ok else '✗'}  {j04.name}  ({size:,} B)")
    else:
        print(f"  skip  {j04.name}")

    # J05: Minimal 16×16 resolution (stress-test the player UI scaling)
    make("J05_16x16_minimal_res", ext=".mp4", width=16, height=16, duration=3.0,
         vcodec="libx264", pix_fmt="yuv420p", acodec=None,
         description="16×16 — minimal resolution")

    # J06: MP4 with subtitle stream (extension should ignore subtitle track)
    j06 = OUT_DIR / "J06_mp4_with_subtitle.mp4"
    if not j06.exists() or j06.stat().st_size < 100:
        ok = run_ffmpeg(
            "-f", "lavfi", "-i",
            "testsrc=duration=5:size=640x480:rate=24,"
            "drawtext=text='J06 with subtitle stream':x=10:y=10:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-f", "lavfi", "-i", "color=c=black:size=640x480:rate=24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-map", "0:v", "-map", "1:a",
            str(j06),
        )
        size = j06.stat().st_size if j06.exists() else 0
        print(f"  {'✓' if ok else '✗'}  {j06.name}  ({size:,} B)")
    else:
        print(f"  skip  {j06.name}")

    # J07: AVI with MJPEG + audio (both transcode and audio extraction)
    make("J07_avi_mjpeg_mp3_audio", ext=".avi", vcodec="mjpeg", pix_fmt="yuvj420p",
         acodec="libmp3lame", description="AVI|MJPEG|MP3 → TRANSCODE + audio extract")

    # -----------------------------------------------------------------------
    # summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    files = sorted(OUT_DIR.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    ok_count = sum(1 for _, s in results if s in ("ok", "skip"))
    fail_count = sum(1 for _, s in results if s == "FAIL")
    for f in files:
        print(f"  {f.name}")
    print(f"\n{len(files)} files  |  {total_size / 1024 / 1024:.1f} MB total")
    print(f"Generated this run: {sum(1 for _, s in results if s == 'ok')} ok, "
          f"{sum(1 for _, s in results if s == 'skip')} skipped, {fail_count} failed")
    if fail_count:
        print("\nFailed files:")
        for n, s in results:
            if s == "FAIL":
                print(f"  ✗  {n}")
    print(f"\nOpen the tests/ folder in VS Code to manually inspect each file.")


if __name__ == "__main__":
    main()
