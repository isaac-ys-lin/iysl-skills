#!/usr/bin/env python3
"""Render a hand-authored SMIL animated SVG into MP4/PNG (and optional GIF).

Pipeline stages:
  (a) structural validation of the SVG source        -> exit 2 on violation
  (b) deterministic browser rendering + quality gate -> exit 1 on failure
  (c) ffmpeg encoding + output contract checks       -> exit 1 on failure

Exit codes match the legacy JSON-spec pipeline:
  0 = all checks passed, outputs written
  1 = quality or output checks failed
  2 = structural validation failed
"""

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

LOOP_MIN_SECONDS = 2.0
LOOP_MAX_SECONDS = 15.0
DEVICE_SCALE_FACTOR = 2
SMIL_TAGS = {"animate", "animateMotion", "animateTransform", "set"}
CJK_FONT_MARKERS = ("PingFang TC", "Noto Sans TC")

CSS_ANIMATION_RE = re.compile(
    r"@keyframes|(?:^|[;{\s])(?:-webkit-)?animation[a-z-]*\s*:"
    r"|(?:^|[;{\s])(?:-webkit-)?transition[a-z-]*\s*:",
    re.IGNORECASE,
)
CSS_IMPORT_RE = re.compile(r"@import\b", re.IGNORECASE)
CSS_EXTERNAL_URL_RE = re.compile(r"url\(\s*['\"]?(?!\s*data:|\s*#)", re.IGNORECASE)


def local_name(tag):
    if isinstance(tag, str):
        return tag.rsplit("}", 1)[-1]
    return ""


def element_hrefs(element):
    values = []
    for key, value in element.attrib.items():
        if local_name(key) == "href":
            values.append(value)
    return values


def parse_view_box(value):
    parts = re.split(r"[\s,]+", value.strip())
    if len(parts) != 4:
        return None
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    return numbers


def validate_structure(svg_text):
    """Return (messages, meta). Empty messages means the SVG passed stage (a)."""
    messages = []
    meta = {"width": None, "height": None, "loop_seconds": None, "poster_t": 0.0}

    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as err:
        return [f"svg_parse_error: SVG is not well-formed XML ({err})"], meta

    if local_name(root.tag) != "svg":
        messages.append(f"root_element: root element must be <svg>, found <{local_name(root.tag)}>")
        return messages, meta

    view_box = root.get("viewBox")
    if view_box is None:
        messages.append("viewbox_missing: root <svg> must declare a viewBox attribute")
    else:
        numbers = parse_view_box(view_box)
        if numbers is None:
            messages.append(f"viewbox_invalid: viewBox must be four numbers, got {view_box!r}")
        elif numbers[2] <= 0 or numbers[3] <= 0:
            messages.append(f"viewbox_invalid: viewBox width/height must be positive, got {view_box!r}")
        else:
            meta["width"] = numbers[2]
            meta["height"] = numbers[3]

    loop_raw = root.get("data-loop-seconds")
    if loop_raw is None:
        messages.append("data-loop-seconds_missing: root <svg> must declare data-loop-seconds (float, 2-15)")
    else:
        try:
            loop_seconds = float(loop_raw)
        except ValueError:
            loop_seconds = None
            messages.append(f"data-loop-seconds_invalid: must be a float, got {loop_raw!r}")
        if loop_seconds is not None:
            if not (LOOP_MIN_SECONDS <= loop_seconds <= LOOP_MAX_SECONDS):
                messages.append(
                    "data-loop-seconds_out_of_range: must be within "
                    f"{LOOP_MIN_SECONDS:g}-{LOOP_MAX_SECONDS:g} seconds, got {loop_seconds:g}"
                )
            else:
                meta["loop_seconds"] = loop_seconds

    poster_raw = root.get("data-poster-t")
    if poster_raw is not None:
        try:
            poster_t = float(poster_raw)
        except ValueError:
            poster_t = None
            messages.append(f"data-poster-t_invalid: must be a float, got {poster_raw!r}")
        if poster_t is not None:
            if poster_t < 0:
                messages.append(f"data-poster-t_invalid: must be >= 0, got {poster_t:g}")
            elif meta["loop_seconds"] is not None and poster_t > meta["loop_seconds"]:
                messages.append(
                    "data-poster-t_out_of_range: must be <= data-loop-seconds "
                    f"({meta['loop_seconds']:g}), got {poster_t:g}"
                )
            else:
                meta["poster_t"] = poster_t

    text_count = 0
    for element in root.iter():
        name = local_name(element.tag)
        if name == "script":
            messages.append("script_forbidden: <script> elements are not allowed; use SMIL animation only")
        elif name == "text":
            text_count += 1
        elif name == "style":
            css = element.text or ""
            if CSS_ANIMATION_RE.search(css):
                messages.append(
                    "css_animation_forbidden: <style> contains @keyframes/animation/transition; "
                    "use SMIL (animate/animateMotion/animateTransform/set) only"
                )
            if CSS_IMPORT_RE.search(css):
                messages.append("external_resource_forbidden: <style> contains @import; SVG must be self-contained")
            if CSS_EXTERNAL_URL_RE.search(css):
                messages.append(
                    "external_resource_forbidden: <style> references a non-data, non-fragment url(); "
                    "embed resources as data URIs"
                )
        elif name == "image":
            hrefs = element_hrefs(element)
            if not hrefs:
                messages.append("image_href_missing: <image> must embed its content as a data URI")
            for href in hrefs:
                if not href.strip().startswith("data:"):
                    messages.append(
                        f"image_external_href_forbidden: <image> href must be a data URI, got {href!r}"
                    )

        style_attr = element.get("style")
        if style_attr:
            if CSS_ANIMATION_RE.search(style_attr):
                messages.append(
                    "css_animation_forbidden: style attribute contains animation/transition on "
                    f"<{name}>; use SMIL only"
                )
            if CSS_EXTERNAL_URL_RE.search(style_attr):
                messages.append(
                    f"external_resource_forbidden: style attribute on <{name}> references an external url()"
                )

        if name != "image":
            for href in element_hrefs(element):
                stripped = href.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("data:"):
                    messages.append(
                        f"external_href_forbidden: <{name}> href must be a fragment or data URI, got {href!r}"
                    )

    if text_count == 0:
        messages.append("text_missing: SVG must contain at least one <text> element")

    if not any(marker in svg_text for marker in CJK_FONT_MARKERS):
        messages.append(
            "cjk_font_fallback_missing: at least one font-family stack must include "
            '"PingFang TC" or "Noto Sans TC"'
        )

    # De-duplicate repeated messages while preserving order.
    seen = set()
    unique = []
    for message in messages:
        if message not in seen:
            seen.add(message)
            unique.append(message)
    return unique, meta


HARNESS_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; background: #ffffff; }}
  body > svg {{ display: block; width: {width}px; height: {height}px; }}
</style>
</head>
<body>
{svg}
</body>
</html>
"""

QUALITY_JS = """
(args) => {
  const svg = document.querySelector('body > svg');
  svg.pauseAnimations();
  const results = { collisions: [], marginViolations: [] };
  const visibleTextUnits = (svgRoot) => {
    const all = Array.from(svgRoot.querySelectorAll('text, tspan'));
    return all.filter((el) => {
      let node = el;
      let opacity = 1;
      while (node && node !== svgRoot) {
        const cs = getComputedStyle(node);
        if (cs.display === 'none' || cs.visibility === 'hidden') return false;
        opacity *= parseFloat(cs.opacity || '1');
        node = node.parentElement;
      }
      if (opacity < 0.05) return false;
      const r = el.getBoundingClientRect();
      return r.width > 0.5 && r.height > 0.5;
    });
  };
  for (const t of args.times) {
    svg.setCurrentTime(t);
    svg.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    const els = visibleTextUnits(svg);
    for (let i = 0; i < els.length; i++) {
      const a = els[i];
      const ra = a.getBoundingClientRect();
      for (let j = i + 1; j < els.length; j++) {
        const b = els[j];
        if (a.contains(b) || b.contains(a)) continue;
        const rb = b.getBoundingClientRect();
        const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
        const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
        if (ox > args.tolerance && oy > args.tolerance) {
          results.collisions.push({
            t: t,
            a: (a.textContent || '').trim().slice(0, 60),
            b: (b.textContent || '').trim().slice(0, 60),
            overlap_px: [Math.round(ox * 10) / 10, Math.round(oy * 10) / 10],
          });
        }
      }
      const distance = Math.min(
        ra.left - svgRect.left,
        ra.top - svgRect.top,
        svgRect.right - ra.right,
        svgRect.bottom - ra.bottom
      );
      if (distance < args.margin) {
        results.marginViolations.push({
          t: t,
          text: (a.textContent || '').trim().slice(0, 60),
          distance_px: Math.round(distance * 10) / 10,
        });
      }
    }
  }
  return results;
}
"""


def ffmpeg_path():
    if Path(FFMPEG).exists():
        return FFMPEG
    found = shutil.which("ffmpeg")
    return found


def ffprobe_path():
    if Path(FFPROBE).exists():
        return FFPROBE
    return shutil.which("ffprobe")


def run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({' '.join(cmd)}): {result.stderr[-800:]}")


def probe_video(path):
    probe = ffprobe_path()
    if probe is None:
        raise RuntimeError("ffprobe not found; cannot verify video output")
    result = subprocess.run(
        [
            probe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[-400:]}")
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(data["format"]["duration"]),
    }


def frame_pixel_activity(path_a, path_b, channel_threshold=8):
    """Count pixels whose channel difference exceeds the threshold."""
    from PIL import Image, ImageChops

    with Image.open(path_a) as im_a, Image.open(path_b) as im_b:
        a = im_a.convert("RGB")
        b = im_b.convert("RGB")
        if a.size != b.size:
            return a.size[0] * a.size[1]
        diff = ImageChops.difference(a, b)
        histogram = diff.histogram()
        changed = 0
        for channel in range(3):
            counts = histogram[channel * 256:(channel + 1) * 256]
            changed = max(changed, sum(counts[channel_threshold + 1:]))
        return changed


def render_pipeline(svg_text, meta, args):
    """Stages (b) and (c). Returns the report dict; caller decides exit code."""
    checks = []
    notes = []
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    loop_seconds = meta["loop_seconds"]
    fps = args.fps
    n_frames = max(2, math.ceil(loop_seconds * fps))
    viewport_w = max(1, math.ceil(meta["width"]))
    viewport_h = max(1, math.ceil(meta["height"]))

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception as err:
            notes.append(
                f"browser_fallback: failed to launch system Chrome channel ({err.__class__.__name__}); "
                "falling back to default chromium"
            )
            browser = p.chromium.launch()

        try:
            page = browser.new_page(
                viewport={"width": viewport_w, "height": viewport_h},
                device_scale_factor=DEVICE_SCALE_FACTOR,
            )
            with tempfile.TemporaryDirectory(prefix="render-svg-") as tmpdir:
                tmp = Path(tmpdir)
                harness = tmp / "harness.html"
                harness.write_text(
                    HARNESS_TEMPLATE.format(width=viewport_w, height=viewport_h, svg=svg_text),
                    encoding="utf-8",
                )
                page.goto(harness.as_uri())
                page.wait_for_selector("body > svg", state="attached")
                svg_el = page.locator("body > svg")

                # --- (b) quality checks -------------------------------------
                quality = page.evaluate(
                    QUALITY_JS,
                    {
                        "times": [0.0, loop_seconds / 2.0],
                        "tolerance": args.collision_tolerance,
                        "margin": args.margin,
                    },
                )
                collisions = quality["collisions"]
                checks.append({
                    "name": "readability_text_collision",
                    "ok": not collisions,
                    "detail": (
                        "no text collisions at t=0 and t=loop/2"
                        if not collisions
                        else "text bounding boxes overlap beyond tolerance "
                        f"({args.collision_tolerance}px): "
                        + "; ".join(
                            f"t={c['t']:g}s {c['a']!r} x {c['b']!r} overlap={c['overlap_px']}px"
                            for c in collisions[:10]
                        )
                    ),
                })
                margin_violations = quality["marginViolations"]
                checks.append({
                    "name": "readability_canvas_margin",
                    "ok": not margin_violations,
                    "detail": (
                        f"all text at least {args.margin}px from the SVG edges"
                        if not margin_violations
                        else f"text closer than {args.margin}px to the SVG edge: "
                        + "; ".join(
                            f"t={v['t']:g}s {v['text']!r} distance={v['distance_px']}px"
                            for v in margin_violations[:10]
                        )
                    ),
                })

                # --- deterministic frame capture ----------------------------
                frames_dir = tmp / "frames"
                frames_dir.mkdir()
                page.evaluate("document.querySelector('body > svg').pauseAnimations()")
                frame_paths = []
                for i in range(n_frames):
                    t = i / fps
                    page.evaluate(
                        "t => document.querySelector('body > svg').setCurrentTime(t)", t
                    )
                    frame_path = frames_dir / f"frame_{i:05d}.png"
                    svg_el.screenshot(path=str(frame_path))
                    frame_paths.append(frame_path)

                # motion_nonzero: 4 equidistant sample frames.
                sample_indices = sorted({0, n_frames // 4, n_frames // 2, (3 * n_frames) // 4})
                samples = [frame_paths[i] for i in sample_indices]
                activities = [
                    frame_pixel_activity(samples[i], samples[i + 1])
                    for i in range(len(samples) - 1)
                ]
                moving = any(activity > 50 for activity in activities)
                checks.append({
                    "name": "motion_nonzero",
                    "ok": moving,
                    "detail": (
                        f"sampled frames {sample_indices} show pixel activity {activities}"
                        if moving
                        else "animation appears static: sampled frames "
                        f"{sample_indices} show near-zero pixel differences {activities}"
                    ),
                })

                # poster frame at data-poster-t
                page.evaluate(
                    "t => document.querySelector('body > svg').setCurrentTime(t)",
                    meta["poster_t"],
                )
                png_path = outdir / f"{args.basename}.png"
                svg_el.screenshot(path=str(png_path))

                # --- (c) encoding -------------------------------------------
                ffmpeg = ffmpeg_path()
                if ffmpeg is None:
                    raise RuntimeError("ffmpeg not found at /opt/homebrew/bin/ffmpeg or on PATH")

                mp4_path = outdir / f"{args.basename}.mp4"
                run_ffmpeg([
                    ffmpeg, "-y",
                    "-framerate", str(fps),
                    "-i", str(frames_dir / "frame_%05d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=white",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(mp4_path),
                ])

                gif_path = None
                if args.gif:
                    gif_path = outdir / f"{args.basename}.gif"
                    palette = tmp / "palette.png"
                    run_ffmpeg([
                        ffmpeg, "-y",
                        "-framerate", str(fps),
                        "-i", str(frames_dir / "frame_%05d.png"),
                        "-vf", "palettegen=stats_mode=diff",
                        str(palette),
                    ])
                    run_ffmpeg([
                        ffmpeg, "-y",
                        "-framerate", str(fps),
                        "-i", str(frames_dir / "frame_%05d.png"),
                        "-i", str(palette),
                        "-lavfi", "paletteuse=dither=sierra2_4a",
                        "-loop", "0",
                        str(gif_path),
                    ])
        finally:
            browser.close()

    # --- output contract checks (outside the browser session) ---------------
    expected_duration = n_frames / fps
    mp4_ok = mp4_path.exists() and mp4_path.stat().st_size > 0
    if mp4_ok:
        info = probe_video(mp4_path)
        duration_ok = abs(info["duration"] - expected_duration) < 0.2
        even_ok = info["width"] % 2 == 0 and info["height"] % 2 == 0
        checks.append({
            "name": "output_mp4",
            "ok": duration_ok and even_ok,
            "detail": (
                f"{mp4_path.name}: {info['width']}x{info['height']}, "
                f"duration {info['duration']:.3f}s (expected {expected_duration:.3f}s +-0.2s), "
                f"even dimensions={even_ok}"
            ),
        })
    else:
        checks.append({
            "name": "output_mp4",
            "ok": False,
            "detail": f"{mp4_path} missing or empty",
        })

    png_ok = png_path.exists() and png_path.stat().st_size > 0
    checks.append({
        "name": "output_png",
        "ok": png_ok,
        "detail": (
            f"{png_path.name}: poster frame at t={meta['poster_t']:g}s "
            f"(device_scale_factor={DEVICE_SCALE_FACTOR})"
            if png_ok
            else f"{png_path} missing or empty"
        ),
    })

    outputs = {"mp4": str(mp4_path), "png": str(png_path)}
    if args.gif:
        gif_ok = gif_path is not None and gif_path.exists() and gif_path.stat().st_size > 0
        checks.append({
            "name": "output_gif",
            "ok": gif_ok,
            "detail": f"{gif_path.name}: palettegen/paletteuse two-pass" if gif_ok else "gif missing or empty",
        })
        outputs["gif"] = str(gif_path) if gif_path else None

    report = {
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
        "outputs": outputs,
        "frames": n_frames,
        "fps": fps,
        "loop_seconds": loop_seconds,
    }
    if notes:
        report["notes"] = notes
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate and render a SMIL animated SVG into MP4/PNG (and optional GIF)."
    )
    parser.add_argument("--svg", required=True, help="Path to the animated SVG file.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    parser.add_argument("--basename", required=True, help="Output basename (NAME.mp4/NAME.png).")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default 30).")
    parser.add_argument("--gif", action="store_true", help="Also encode NAME.gif.")
    parser.add_argument(
        "--collision-tolerance", type=float, default=2.0,
        help="Max text bbox overlap in px on both axes before failing (default 2).",
    )
    parser.add_argument(
        "--margin", type=float, default=8.0,
        help="Min distance in px between text and the SVG edge (default 8).",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Print the JSON check report to stdout.",
    )
    args = parser.parse_args()

    svg_path = Path(args.svg)
    if not svg_path.exists():
        print(json.dumps({"ok": False, "messages": [f"svg_not_found: {svg_path}"]},
                         ensure_ascii=False, indent=2))
        sys.exit(2)

    svg_text = svg_path.read_text(encoding="utf-8")
    messages, meta = validate_structure(svg_text)
    if messages:
        print(json.dumps({"ok": False, "messages": messages}, ensure_ascii=False, indent=2))
        sys.exit(2)

    try:
        report = render_pipeline(svg_text, meta, args)
    except Exception as err:
        report = {
            "ok": False,
            "checks": [{
                "name": "render_pipeline",
                "ok": False,
                "detail": f"{err.__class__.__name__}: {err}",
            }],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
