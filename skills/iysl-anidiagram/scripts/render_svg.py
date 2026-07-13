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
from contextlib import contextmanager
import fcntl
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

LOOP_MIN_SECONDS = 2.0
LOOP_MAX_SECONDS = 15.0
DEVICE_SCALE_FACTOR = 2
SMIL_TAGS = {"animate", "animateMotion", "animateTransform", "set"}
CJK_FONT_MARKERS = ("PingFang TC", "Noto Sans TC")
ACTIVE_SVG_ELEMENTS = {"foreignObject", "iframe", "object", "embed", "audio", "video"}
ALLOWED_SVG_ELEMENTS = {
    "svg", "g", "defs", "symbol", "use", "title", "desc", "metadata", "switch",
    "rect", "circle", "ellipse", "line", "polyline", "polygon", "path",
    "text", "tspan", "image", "pattern", "clipPath", "mask", "marker",
    "linearGradient", "radialGradient", "stop", "filter",
    "feColorMatrix", "feComposite", "feDisplacementMap", "feFlood",
    "feGaussianBlur", "feMerge", "feMergeNode", "feOffset", "feBlend",
    "feTurbulence", "animate", "animateMotion", "animateTransform", "set", "mpath",
}
DEFAULT_RENDER_LOCK = Path(tempfile.gettempdir()) / "iysl-anidiagram-render.lock"

CSS_ANIMATION_RE = re.compile(
    r"@keyframes|(?:^|[;{\s])(?:-webkit-)?animation[a-z-]*\s*:"
    r"|(?:^|[;{\s])(?:-webkit-)?transition[a-z-]*\s*:",
    re.IGNORECASE,
)
CSS_IMPORT_RE = re.compile(r"@import\b", re.IGNORECASE)
CSS_EXTERNAL_URL_RE = re.compile(r"url\(\s*['\"]?(?!\s*data:|\s*#)", re.IGNORECASE)
CSS_OBFUSCATION_RE = re.compile(r"\\|/\*")


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


def split_smil_values(value):
    if value is None:
        return []
    return [part.strip() for part in value.split(";")]


def spline_validation_messages(element):
    """Return stable structural errors for incomplete or invalid SMIL spline metadata."""
    messages = []
    calc_mode = element.get("calcMode")
    raw_splines = element.get("keySplines")
    if raw_splines is None and calc_mode != "spline":
        return messages
    if raw_splines is not None and calc_mode != "spline":
        messages.append("spline_calc_mode_missing: keySplines requires calcMode='spline'")
        return messages
    if calc_mode == "spline" and raw_splines is None:
        messages.append("spline_key_splines_missing: calcMode='spline' requires keySplines")
        return messages

    splines = split_smil_values(raw_splines)
    values = split_smil_values(element.get("values"))
    key_times = split_smil_values(element.get("keyTimes"))
    if any(not value for value in values + key_times):
        messages.append("spline_empty_stop_invalid: values/keyTimes may not contain empty stops")
    if values and key_times and len(values) != len(key_times):
        messages.append(
            "spline_key_times_count_invalid: keyTimes must contain one entry per values stop"
        )
    if key_times:
        try:
            parsed_times = [float(value) for value in key_times]
        except ValueError:
            parsed_times = []
        valid_times = (
            len(parsed_times) == len(key_times)
            and all(math.isfinite(value) and 0 <= value <= 1 for value in parsed_times)
            and all(left <= right for left, right in zip(parsed_times, parsed_times[1:]))
            and parsed_times[0] == 0
            and parsed_times[-1] == 1
        )
        if not valid_times:
            messages.append(
                "spline_key_times_invalid: keyTimes must be finite, nondecreasing values "
                "in [0,1] that start at 0 and end at 1"
            )
    stop_count = len(key_times) or len(values) or 2
    expected = max(1, stop_count - 1)
    if len(splines) != expected:
        messages.append(
            f"spline_count_invalid: expected {expected} keySplines groups, got {len(splines)}"
        )

    for index, spline in enumerate(splines, start=1):
        try:
            points = [float(value) for value in re.split(r"[\s,]+", spline.strip())]
        except ValueError:
            points = []
        if len(points) != 4 or any(
            not math.isfinite(point) or point < 0 or point > 1 for point in points
        ):
            messages.append(
                "spline_control_point_invalid: keySplines group "
                f"{index} must contain four numbers in [0,1]"
            )
    return messages


def has_valid_spline(element):
    return element.get("calcMode") == "spline" and not spline_validation_messages(element)


@contextmanager
def exclusive_render_lock(lock_path=DEFAULT_RENDER_LOCK, timeout=180.0):
    """Serialize browser capture across Creative subprocesses.

    Creative work remains parallel; only the Chrome/ffmpeg critical section queues.
    Advisory locks are released automatically if a renderer exits or crashes.
    """
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"timed out after {timeout:g}s waiting for render lock {lock_path}"
                    )
                time.sleep(min(0.05, remaining))
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
        elif name in ACTIVE_SVG_ELEMENTS or name not in ALLOWED_SVG_ELEMENTS:
            messages.append(
                f"active_content_forbidden: unsupported <{name}> is not allowed in rendered SVG input"
            )
        elif name == "text":
            text_count += 1
        elif name == "style":
            css = element.text or ""
            if CSS_OBFUSCATION_RE.search(css):
                messages.append(
                    "active_content_forbidden: CSS escapes/comments are not allowed in <style>"
                )
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
            messages.append(
                f"active_content_forbidden: style attributes are not allowed on <{name}>; "
                "use SVG presentation attributes"
            )
            if CSS_OBFUSCATION_RE.search(style_attr):
                messages.append(
                    f"active_content_forbidden: CSS escapes/comments are not allowed in style on <{name}>"
                )
            if CSS_ANIMATION_RE.search(style_attr):
                messages.append(
                    "css_animation_forbidden: style attribute contains animation/transition on "
                    f"<{name}>; use SMIL only"
                )
            if CSS_EXTERNAL_URL_RE.search(style_attr):
                messages.append(
                    f"external_resource_forbidden: style attribute on <{name}> references an external url()"
                )

        for attribute, value in element.attrib.items():
            if CSS_OBFUSCATION_RE.search(value):
                messages.append(
                    f"active_content_forbidden: CSS escapes/comments are not allowed in <{name}> attributes"
                )
            if local_name(attribute).lower().startswith("on"):
                messages.append(
                    f"active_content_forbidden: event attribute {local_name(attribute)!r} "
                    f"is not allowed on <{name}>"
                )
            if local_name(attribute).lower() == "src":
                messages.append(
                    f"active_content_forbidden: src is not allowed on <{name}>"
                )
            if CSS_EXTERNAL_URL_RE.search(value):
                messages.append(
                    "active_content_forbidden: SVG attributes may reference only "
                    f"fragment or data url() values; found external URL on <{name}>"
                )

        if name in SMIL_TAGS:
            dynamic_attribute = local_name(element.get("attributeName") or "").lower()
            dynamic_attribute = dynamic_attribute.rsplit(":", 1)[-1]
            if dynamic_attribute.startswith("on") or dynamic_attribute in {"href", "src", "style"}:
                messages.append(
                    "active_content_forbidden: SMIL may not mutate href, src, style, "
                    "or event attributes"
                )

        if name in ("animate", "animateTransform"):
            messages.extend(spline_validation_messages(element))

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


def scan_motion_warnings(svg_text):
    """Non-blocking advisories. These never affect the check result or exit code.

    Flags motion that is overwhelmingly raw-linear: SMIL defaults to
    calcMode="linear", which reads mechanical for reveals. animateMotion is
    excluded (path-following is legitimately linear)."""
    warnings = []
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError:
        return warnings

    easable = 0
    eased = 0
    for element in root.iter():
        if local_name(element.tag) not in ("animate", "animateTransform"):
            continue
        values = element.get("values")
        if not values or len([s for s in values.split(";") if s.strip()]) < 2:
            continue
        if element.get("calcMode") == "discrete":
            continue
        easable += 1
        if has_valid_spline(element):
            eased += 1

    if easable >= 6 and (eased / easable) < 0.15:
        warnings.append(
            f"motion_mostly_linear: {easable - eased} of {easable} value-based animations use "
            "raw linear interpolation (no keySplines). SMIL defaults to linear, which reads "
            'mechanical; add calcMode="spline" with ease-out keySplines "0.23 1 0.32 1" to reveals '
            "(keep linear only for continuous loops). See references/animation-semantics.md."
        )
    return warnings


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

SEEK_AND_PAINT_JS = """
async (t) => {
  const svg = document.querySelector('body > svg');
  svg.setCurrentTime(t);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  svg.getBoundingClientRect();
}
"""

LOOP_SEAM_JS = """
async (args) => {
  const svg = document.querySelector('body > svg');
  svg.pauseAnimations();
  const animations = Array.from(svg.querySelectorAll(
    'animate, animateTransform, animateMotion, set'
  ));
  const targets = Array.from(new Set(animations.map((animation) => animation.parentElement)));
  const visibilityOf = (element) => {
    let opacity = 1;
    let node = element;
    while (node && node !== svg) {
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden' || style.visibility === 'collapse') {
        return 0;
      }
      opacity *= Number.parseFloat(style.opacity || '1');
      node = node.parentElement;
    }
    return opacity;
  };
  const snapshot = () => targets.map((element) => {
    const rect = element.getBoundingClientRect();
    return {
      tag: element.tagName,
      x: rect.x + rect.width / 2,
      y: rect.y + rect.height / 2,
      opacity: visibilityOf(element),
    };
  });
  const times = [0, args.epsilon, args.loop - 2 * args.epsilon, args.loop - args.epsilon];
  const states = [];
  for (const t of times) {
    svg.setCurrentTime(Math.max(0, t));
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    states.push(snapshot());
  }
  const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const violations = [];
  targets.forEach((element, index) => {
    const start = states[0][index];
    const startNext = states[1][index];
    const endPrevious = states[2][index];
    const end = states[3][index];
    if (start.opacity < args.opacity || end.opacity < args.opacity) return;
    const seam = distance(end, start);
    const normalStep = Math.max(distance(start, startNext), distance(endPrevious, end), 1);
    if (seam > Math.max(args.minJump, normalStep * args.multiplier)) {
      violations.push({
        tag: start.tag,
        seam: Math.round(seam * 10) / 10,
        normalStep: Math.round(normalStep * 10) / 10,
      });
    }
  });
  return violations;
}
"""


def seek_and_wait_for_paint(page, timestamp):
    page.evaluate(SEEK_AND_PAINT_JS, timestamp)


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
                harness_uri = harness.as_uri()
                blocked_requests = []

                def guard_request(route):
                    request = route.request
                    if request.is_navigation_request() and request.url == harness_uri:
                        route.continue_()
                    else:
                        blocked_requests.append(request.url)
                        route.abort()

                page.route("**/*", guard_request)
                page.goto(harness_uri)
                page.wait_for_selector("body > svg", state="attached")
                page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
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
                    seek_and_wait_for_paint(page, t)
                    frame_path = frames_dir / f"frame_{i:05d}.png"
                    svg_el.screenshot(path=str(frame_path))
                    frame_paths.append(frame_path)

                seam_violations = page.evaluate(
                    LOOP_SEAM_JS,
                    {
                        "loop": loop_seconds,
                        "epsilon": 1 / fps,
                        "opacity": 0.05,
                        "minJump": 24,
                        "multiplier": 4,
                    },
                )
                checks.append({
                    "name": "loop_position_seam",
                    "ok": not seam_violations,
                    "detail": (
                        "no visible animated target jumps across the loop boundary"
                        if not seam_violations
                        else "visible loop-boundary position jumps: "
                        + "; ".join(
                            f"<{item['tag']}> seam={item['seam']}px "
                            f"normal_step={item['normalStep']}px"
                            for item in seam_violations[:10]
                        )
                    ),
                })

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
                seek_and_wait_for_paint(page, meta["poster_t"])
                png_path = outdir / f"{args.basename}.png"
                svg_el.screenshot(path=str(png_path))
                checks.append({
                    "name": "external_resource_runtime",
                    "ok": not blocked_requests,
                    "detail": (
                        "browser emitted no subresource requests"
                        if not blocked_requests
                        else "blocked external/local subresource requests: "
                        + "; ".join(blocked_requests[:10])
                    ),
                })

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
        with exclusive_render_lock():
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

    warnings = scan_motion_warnings(svg_text)
    if warnings:
        report.setdefault("warnings", []).extend(warnings)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
