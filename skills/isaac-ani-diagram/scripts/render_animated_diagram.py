#!/usr/bin/env python3
import argparse
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


DEFAULT_W = 1210
DEFAULT_H = 1138
DEFAULT_FRAMES = 41
DEFAULT_FPS = 20
SCALE = 2
UPDATED = 1782475200000

THEME = {
    "bg": "#000000",
    "white": "#f4f0ee",
    "muted": "#cfc7c5",
    "frame": "#5c6265",
    "core_fill": "#04171e",
    "core_stroke": "#1d8be8",
    "green": "#22c86f",
    "green_fill": "#02160a",
    "purple": "#bd54d3",
    "purple_fill": "#120814",
    "cyan": "#7ee3d6",
    "blue_fill": "#081626",
    "highlight": "#124238",
    "amber": "#f4b64e",
    "pink": "#ff7ab6",
    "archive_fill": "#080711",
    "source_fill": "#02160a",
    "pack_fill": "#04180d",
}

LIGHT_THEME = {
    "background": "#f3f7fc",
    "primary": "#2459c7",
    "primary_soft": "#dce8fb",
    "muted": "#6b7890",
    "border": "#b8c8ee",
    "text": "#182032",
    "card": "#eef3fa",
    "white": "#ffffff",
}

DARK_TECHNICAL_THEME = {
    "background": THEME["bg"],
    "primary": THEME["green"],
    "primary_soft": "#08291a",
    "muted": THEME["muted"],
    "border": THEME["frame"],
    "text": THEME["white"],
    "card": THEME["core_fill"],
    "white": THEME["bg"],
}

LIGHT_LAYOUTS = {
    "circular_loop",
    "timeline",
    "funnel",
    "matrix",
    "stack",
    "before_after",
}


def hex_rgba(value, alpha=255):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def c(v):
    return int(round(v * SCALE))


def scaled_box(x, y, w, h):
    return (c(x), c(y), c(x + w), c(y + h))


def font_candidates(hand=False, cjk=False, bold=False):
    if hand:
        return [
            "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
            "/System/Library/Fonts/MarkerFelt.ttc",
            "/System/Library/Fonts/Noteworthy.ttc",
            "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
        ]
    if cjk:
        return [
            "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        ]
    return [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]


def load_font(size, hand=False, cjk=False, bold=False):
    for path in font_candidates(hand=hand, cjk=cjk, bold=bold):
        try:
            return ImageFont.truetype(path, c(size))
        except OSError:
            continue
    return ImageFont.load_default()


def has_cjk(text):
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def text_size(draw, text, font, spacing=3):
    if not text:
        return 0, 0
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=c(spacing))
    return box[2] - box[0], box[3] - box[1]


def wrap_token(draw, token, font, max_width):
    if not token:
        return [token]
    parts = []
    current = ""
    for char in token:
        candidate = current + char
        if current and text_size(draw, candidate, font)[0] > max_width:
            parts.append(current)
            current = char
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def wrap_line(draw, line, font, max_width):
    if not line:
        return [line]
    tokens = list(line) if has_cjk(line) else line.split(" ")
    separator = "" if has_cjk(line) else " "
    lines = []
    current = ""
    for token in tokens:
        candidate = token if not current else current + separator + token
        if text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        if text_size(draw, token, font)[0] <= max_width:
            current = token
        else:
            split_parts = wrap_token(draw, token, font, max_width)
            lines.extend(split_parts[:-1])
            current = split_parts[-1] if split_parts else ""
    if current:
        lines.append(current)
    return lines


def wrap_text(draw, text, font, max_width):
    lines = []
    for raw_line in str(text).splitlines() or [""]:
        lines.extend(wrap_line(draw, raw_line, font, max_width))
    return "\n".join(lines)


EMERGENCY_MIN_TEXT_SIZE = 6


def text_variants(draw, text, font, max_width, wrap):
    raw = str(text)
    if not wrap:
        return [raw]
    wrapped = wrap_text(draw, raw, font, max_width)
    if wrapped == raw:
        return [wrapped]
    return [wrapped, raw]


def fit_text(draw, text, w, h, size, min_size=10, hand=False, bold=False, spacing=3, wrap=True):
    raw_text = str(text)
    has_cjk_text = has_cjk(raw_text)
    max_width = c(w)
    max_height = c(h)
    start_size = int(size)
    emergency_min = min(start_size, int(min_size), EMERGENCY_MIN_TEXT_SIZE)
    for candidate_size in range(start_size, emergency_min - 1, -1):
        candidate_font = load_font(candidate_size, hand=hand and not has_cjk_text, cjk=has_cjk_text, bold=bold)
        for candidate_text in text_variants(draw, raw_text, candidate_font, max_width, wrap):
            tw, th = text_size(draw, candidate_text, candidate_font, spacing=spacing)
            if tw <= max_width and th <= max_height:
                return candidate_text, candidate_size, candidate_font

    fallback_font = load_font(emergency_min, hand=hand and not has_cjk_text, cjk=has_cjk_text, bold=bold)
    fallback_text = wrap_text(draw, raw_text, fallback_font, max_width) if wrap else raw_text
    return fallback_text, emergency_min, fallback_font


class Excal:
    def __init__(self, width, height, background=None):
        self.width = width
        self.height = height
        self.background = background or THEME["bg"]
        self.elements = []
        self.count = 0
        self.rng = random.Random(2069769416930414980)

    def base(self, prefix, kind, x, y, w, h, stroke, fill="transparent", stroke_width=2, stroke_style="solid", roundness=None):
        self.count += 1
        element = {
            "id": f"{prefix}-{self.count:04d}",
            "type": kind,
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(w, 2),
            "height": round(h, 2),
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": fill or "transparent",
            "fillStyle": "solid",
            "strokeWidth": stroke_width,
            "strokeStyle": stroke_style,
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": f"a{self.count:04d}",
            "roundness": roundness,
            "seed": self.rng.randint(1, 2147483646),
            "version": 1,
            "versionNonce": self.rng.randint(1, 2147483646),
            "isDeleted": False,
            "boundElements": None,
            "updated": UPDATED,
            "link": None,
            "locked": False,
        }
        self.elements.append(element)
        return element

    def rect(self, x, y, w, h, stroke, fill="transparent", width=2, style="solid"):
        return self.base("rect", "rectangle", x, y, w, h, stroke, fill, width, style, {"type": 3})

    def ellipse(self, x, y, w, h, stroke, fill="transparent", width=2, style="solid"):
        return self.base("ellipse", "ellipse", x, y, w, h, stroke, fill, width, style, None)

    def diamond(self, x, y, w, h, stroke, fill="transparent", width=2):
        return self.base("diamond", "diamond", x, y, w, h, stroke, fill, width, "solid", {"type": 2})

    def text(self, text, x, y, w, h, size, color, align="left"):
        element = self.base("text", "text", x, y, w, h, color, "transparent", 1, "solid", None)
        element.update(
            {
                "text": text,
                "fontSize": int(round(size)),
                "fontFamily": 5,
                "textAlign": align,
                "verticalAlign": "top",
                "baseline": int(round(size * 1.25)),
                "containerId": None,
                "originalText": text,
                "lineHeight": 1.25,
            }
        )
        return element

    def line(self, points, stroke, width=2, style="solid", arrow=False):
        kind = "arrow" if arrow else "line"
        min_x = min(x for x, _ in points)
        min_y = min(y for _, y in points)
        max_x = max(x for x, _ in points)
        max_y = max(y for _, y in points)
        element = self.base(
            kind,
            kind,
            min_x,
            min_y,
            max_x - min_x,
            max_y - min_y,
            stroke,
            "transparent",
            width,
            style,
            {"type": 2},
        )
        element["points"] = [[round(x - min_x, 2), round(y - min_y, 2)] for x, y in points]
        element["startBinding"] = None
        element["endBinding"] = None
        return element

    def write(self, path):
        data = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": self.elements,
            "appState": {
                "viewBackgroundColor": self.background,
                "gridSize": 20,
                "currentItemFontFamily": 5,
            },
            "files": {},
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def draw_text(ex, draw, text, x, y, w, h, size, color=None, align="center", hand=False, bold=False, spacing=3, fit=False, min_size=10, wrap=True):
    color = color or THEME["white"]
    if fit:
        text, size, font = fit_text(draw, text, w, h, size, min_size=min_size, hand=hand, bold=bold, spacing=spacing, wrap=wrap)
    else:
        font = load_font(size, hand=hand and not has_cjk(text), cjk=has_cjk(text), bold=bold)
    ex.text(text, x, y, w, h, size, color, align=align)
    tw, th = text_size(draw, text, font, spacing=spacing)
    tx = c(x)
    if align == "center":
        tx = c(x) + (c(w) - tw) / 2
    elif align == "right":
        tx = c(x + w) - tw
    ty = c(y) + (c(h) - th) / 2
    draw.multiline_text((tx, ty), text, font=font, fill=hex_rgba(color), spacing=c(spacing), align=align)


def draw_rect(ex, draw, x, y, w, h, stroke, fill=None, width=2, radius=10, style="solid"):
    ex.rect(x, y, w, h, stroke, fill or "transparent", width, style)
    draw.rounded_rectangle(scaled_box(x, y, w, h), radius=c(radius), outline=hex_rgba(stroke), fill=hex_rgba(fill) if fill else None, width=max(1, c(width)))


def draw_ellipse(ex, draw, x, y, w, h, stroke, fill=None, width=2):
    ex.ellipse(x, y, w, h, stroke, fill or "transparent", width)
    draw.ellipse(scaled_box(x, y, w, h), outline=hex_rgba(stroke), fill=hex_rgba(fill) if fill else None, width=max(1, c(width)))


def draw_line(ex, draw, points, stroke, width=2, style="solid", arrow=False):
    ex.line(points, stroke, width, style, arrow)
    scaled = [(c(x), c(y)) for x, y in points]
    if style == "solid":
        draw.line(scaled, fill=hex_rgba(stroke), width=max(1, c(width)), joint="curve")
    else:
        total = path_len(points)
        dist = 0
        dash = 8 if style == "dashed" else 2
        gap = 8 if style == "dashed" else 7
        while dist < total:
            start = point_at_distance(points, dist)
            end = point_at_distance(points, min(total, dist + dash))
            draw.line([(c(start[0]), c(start[1])), (c(end[0]), c(end[1]))], fill=hex_rgba(stroke), width=max(1, c(width)))
            dist += dash + gap
    if arrow and len(points) >= 2:
        arrow_head(draw, points[-2], points[-1], stroke, width)


def draw_diamond(ex, draw, x, y, w, h, stroke, fill=None, width=2):
    ex.diamond(x, y, w, h, stroke, fill or "transparent", width)
    pts = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
    scaled = [(c(px), c(py)) for px, py in pts]
    draw.polygon(scaled, outline=hex_rgba(stroke), fill=hex_rgba(fill) if fill else None)
    draw.line(scaled + [scaled[0]], fill=hex_rgba(stroke), width=max(1, c(width)))


def path_len(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def point_at_distance(points, distance):
    left = distance
    for a, b in zip(points, points[1:]):
        seg = math.dist(a, b)
        if seg == 0:
            continue
        if left <= seg:
            t = left / seg
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        left -= seg
    return points[-1]


def point_at_fraction(points, t):
    total = path_len(points)
    return point_at_distance(points, (t % 1.0) * total)


def arrow_head(draw, a, b, stroke, width=2):
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    length = 14 + width
    spread = 0.52
    p1 = (b[0] - length * math.cos(angle - spread), b[1] - length * math.sin(angle - spread))
    p2 = (b[0] - length * math.cos(angle + spread), b[1] - length * math.sin(angle + spread))
    draw.line([(c(p1[0]), c(p1[1])), (c(b[0]), c(b[1])), (c(p2[0]), c(p2[1]))], fill=hex_rgba(stroke), width=max(1, c(width)))


def icon(ex, draw, kind, x, y, color=None, scale=1.0):
    color = color or THEME["cyan"]
    if kind == "folder":
        draw_line(ex, draw, [(x, y + 9 * scale), (x, y + 35 * scale), (x + 48 * scale, y + 35 * scale), (x + 48 * scale, y + 7 * scale), (x + 26 * scale, y + 7 * scale), (x + 21 * scale, y), (x + 2 * scale, y), (x + 2 * scale, y + 9 * scale)], THEME["white"], 2)
        draw_rect(ex, draw, x + 5 * scale, y + 15 * scale, 38 * scale, 15 * scale, color, color, 1, 3)
    elif kind == "file":
        draw_rect(ex, draw, x + 7 * scale, y, 33 * scale, 36 * scale, THEME["white"], color, 2, 4)
        draw_line(ex, draw, [(x + 15 * scale, y + 14 * scale), (x + 31 * scale, y + 14 * scale)], THEME["bg"], 2)
        draw_line(ex, draw, [(x + 15 * scale, y + 24 * scale), (x + 31 * scale, y + 24 * scale)], THEME["bg"], 2)
    elif kind == "scan":
        draw_ellipse(ex, draw, x + 14, y + 11, 38, 38, THEME["white"], None, 4)
        draw_line(ex, draw, [(x + 47, y + 45), (x + 64, y + 62)], THEME["white"], 5)
    elif kind == "shield":
        pts = [(x + 38, y + 7), (x + 63, y + 17), (x + 58, y + 47), (x + 38, y + 65), (x + 18, y + 47), (x + 13, y + 17)]
        draw.polygon([(c(px), c(py)) for px, py in pts], fill=hex_rgba(THEME["green"], 180), outline=hex_rgba(THEME["white"]))
        draw_line(ex, draw, pts + [pts[0]], THEME["white"], 3)
        draw_line(ex, draw, [(x + 27, y + 37), (x + 36, y + 48), (x + 51, y + 27)], THEME["white"], 4)
    elif kind == "db":
        draw_ellipse(ex, draw, x + 15, y + 9, 50, 17, THEME["white"], color, 2)
        draw_rect(ex, draw, x + 15, y + 17, 50, 37, THEME["white"], color, 2, 0)
        draw_ellipse(ex, draw, x + 15, y + 45, 50, 17, THEME["white"], color, 2)
    elif kind == "hash":
        draw_line(ex, draw, [(x + 27, y + 14), (x + 22, y + 58)], THEME["amber"], 4)
        draw_line(ex, draw, [(x + 50, y + 14), (x + 45, y + 58)], THEME["amber"], 4)
        draw_line(ex, draw, [(x + 15, y + 29), (x + 62, y + 29)], THEME["white"], 4)
        draw_line(ex, draw, [(x + 13, y + 45), (x + 60, y + 45)], THEME["white"], 4)
    elif kind == "package":
        draw_line(ex, draw, [(x + 38, y + 8), (x + 66, y + 23), (x + 66, y + 52), (x + 38, y + 68), (x + 10, y + 52), (x + 10, y + 23), (x + 38, y + 8)], THEME["white"], 3)
        draw_line(ex, draw, [(x + 10, y + 23), (x + 38, y + 38), (x + 66, y + 23)], THEME["amber"], 3)
        draw_line(ex, draw, [(x + 38, y + 38), (x + 38, y + 68)], THEME["amber"], 3)
    else:
        draw_ellipse(ex, draw, x + 18, y + 18, 36, 36, color, color, 2)


def draw_signature(ex, draw, text, x, y):
    ex.text(text, x, y, 120, 36, 23, THEME["white"], align="left")
    font = load_font(24, cjk=True, bold=True)
    sx, sy = c(x), c(y)
    for dx, dy, color, alpha in [(-1, 1, THEME["purple"], 165), (1, -1, THEME["cyan"], 135), (0, 0, THEME["white"], 245)]:
        draw.text((sx + c(dx), sy + c(dy)), text, font=font, fill=hex_rgba(color, alpha))
    draw.line([(sx + 6, sy + 56), (sx + 28, sy + 61), (sx + 62, sy + 58), (sx + 86, sy + 63)], fill=hex_rgba(THEME["purple"], 170), width=3)
    draw.line([(sx + 8, sy + 54), (sx + 84, sy + 60)], fill=hex_rgba(THEME["white"], 125), width=1)


def brand(ex, draw, signature):
    dots = [
        (0, 0, THEME["cyan"]),
        (10, 8, THEME["white"]),
        (0, 16, THEME["purple"]),
        (10, 24, THEME["white"]),
        (20, 0, THEME["white"]),
        (30, 8, THEME["pink"]),
        (20, 16, THEME["white"]),
        (30, 24, THEME["green"]),
    ]
    for dx, dy, color in dots:
        draw_ellipse(ex, draw, 955 + dx, 143 + dy, 5, 5, color, color, 1)
    draw_signature(ex, draw, signature, 998, 135)


def small_input(ex, draw, x, y, item):
    kind = item.get("icon", "file")
    color = item.get("color", THEME["cyan"])
    icon(ex, draw, kind, x + 15, y + 1, color, 0.9)
    draw_text(ex, draw, item.get("label", ""), x - 5, y + 42, 78, 24, 13, THEME["white"], "center", fit=True, min_size=9)


def core_card(ex, draw, x, y, card):
    draw_rect(ex, draw, x, y, 260, 90, THEME["core_stroke"], THEME["blue_fill"], 2, 9)
    icon(ex, draw, card.get("icon", "file"), x + 14, y + 13, card.get("color", THEME["cyan"]))
    draw_text(ex, draw, card.get("title", ""), x + 110, y + 11, 100, 28, 20, THEME["white"], "center", hand=True, bold=True, fit=True, min_size=15)
    draw_text(ex, draw, card.get("body", ""), x + 92, y + 42, 150, 38, 14, THEME["white"], "center", spacing=3, fit=True, min_size=11)


def mini_card(ex, draw, x, y, w, h, card, stroke, fill):
    draw_rect(ex, draw, x, y, w, h, stroke, fill, 2, 8)
    icon(ex, draw, card.get("icon", "file"), x + 10, y + 10, card.get("color", THEME["cyan"]))
    draw_text(ex, draw, card.get("title", ""), x + 78, y + 12, 115, 24, 17, THEME["white"], "left", bold=True, fit=True, min_size=12)
    draw_text(ex, draw, card.get("body", ""), x + 78, y + 38, w - 92, h - 43, 12, THEME["white"], "left", spacing=3, fit=True, min_size=10)


def pack_row(ex, draw, x, y, card):
    draw_rect(ex, draw, x, y, 228, 84, THEME["green"], "#04200f", 2, 8)
    icon(ex, draw, card.get("icon", "file"), x + 12, y + 10, card.get("color", THEME["cyan"]))
    draw_text(ex, draw, card.get("title", ""), x + 86, y + 12, 120, 25, 17, THEME["white"], "center", bold=True, fit=True, min_size=12)
    draw_text(ex, draw, card.get("body", ""), x + 80, y + 42, 135, 30, 12, THEME["white"], "center", spacing=3, fit=True, min_size=10)


def layout_name(spec):
    return spec.get("layout") or spec.get("type") or "architecture"


IR_RELATION_LAYOUTS = {
    "sequence": "timeline",
    "process": "timeline",
    "timeline": "timeline",
    "loop": "circular_loop",
    "cycle": "circular_loop",
    "funnel": "funnel",
    "matrix": "matrix",
    "tradeoff": "matrix",
    "stack": "stack",
    "layers": "stack",
    "before_after": "before_after",
    "contrast": "before_after",
    "architecture": "architecture",
}


def is_diagram_ir(raw):
    return isinstance(raw, dict) and isinstance(raw.get("diagram_ir"), dict)


def compile_diagram_ir(ir):
    relation = str(ir.get("relation", "sequence")).strip().lower()
    layout = IR_RELATION_LAYOUTS.get(relation, "timeline")
    nodes = list(ir.get("nodes", []))
    title = dict(ir.get("title") or {})
    title.setdefault("main", ir.get("claim", "Diagram"))
    title.setdefault("subtitle", ir.get("subtitle", ""))

    def node_base(node, primary="label", secondary=None, defaults=None):
        item = {primary: node.get("label", node.get("id", ""))}
        if secondary:
            item[secondary] = node.get(secondary, "")
        if defaults:
            item.update(defaults(node))
        if isinstance(node.get("style"), dict):
            item["style"] = node["style"]
        return item

    spec = {"layout": layout, "title": title}
    if ir.get("layout_reason"):
        spec["layout_reason"] = ir["layout_reason"]
    for key in ("canvas", "palette", "animation", "style", "finish"):
        if key in ir:
            spec[key] = ir[key]

    if layout == "timeline":
        spec["steps"] = [node_base(n, "label", "body") for n in nodes]
    elif layout == "circular_loop":
        spec["steps"] = [node_base(n, "label", "badge") for n in nodes]
    elif layout == "funnel":
        spec["stages"] = [node_base(n, "label", "value") for n in nodes]
    elif layout == "stack":
        spec["layers"] = [node_base(n, "label", "body") for n in nodes]
    elif layout == "matrix":
        spec["items"] = [node_base(n, "label", defaults=lambda node: {"x": node.get("x", 0.5), "y": node.get("y", 0.5)}) for n in nodes]
        spec["x_axis"] = ir.get("x_axis", "Effort")
        spec["y_axis"] = ir.get("y_axis", "Impact")
    elif layout == "before_after":
        spec["before"] = ir.get("before", {"title": "Before", "items": []})
        spec["after"] = ir.get("after", {"title": "After", "items": []})
    return spec


def normalize_render_input(raw):
    if is_diagram_ir(raw):
        return compile_diagram_ir(raw["diagram_ir"])
    return raw


def is_light_layout(spec):
    return layout_name(spec) in LIGHT_LAYOUTS


def style_tone(spec):
    return str(spec.get("style", {}).get("tone", "light_editorial")).strip().lower()


def light_theme_defaults(spec):
    if style_tone(spec) == "dark_technical":
        return DARK_TECHNICAL_THEME
    return LIGHT_THEME


def merged_palette(spec, defaults):
    palette = dict(defaults)
    palette.update(spec.get("palette", {}))
    if "chip" in palette and "primary_soft" not in spec.get("palette", {}):
        palette["primary_soft"] = palette["chip"]
    return palette


def block_style(item):
    if isinstance(item, dict) and isinstance(item.get("style"), dict):
        return item["style"]
    return {}


def style_value(style, keys, fallback):
    for key in keys:
        value = style.get(key)
        if value:
            return value
    return fallback


def light_style_colors(palette, item=None, defaults=None):
    defaults = defaults or {}
    style = block_style(item)
    accent = style_value(style, ("accent", "primary"), defaults.get("accent", palette["primary"]))
    stroke = style_value(style, ("stroke", "border"), defaults.get("stroke", palette["border"]))
    fill = style_value(style, ("fill", "background"), defaults.get("fill", palette["card"]))
    text = style_value(style, ("text",), defaults.get("text", palette["text"]))
    muted = style_value(style, ("muted", "body_text"), defaults.get("muted", palette["muted"]))
    value = style_value(style, ("value",), defaults.get("value", accent))
    index_text = style_value(style, ("index_text",), defaults.get("index_text", palette["white"]))
    return {
        "accent": accent,
        "stroke": stroke,
        "fill": fill,
        "text": text,
        "muted": muted,
        "value": value,
        "index_text": index_text,
    }


def light_canvas(spec):
    canvas = spec.get("canvas", {})
    width = canvas.get("width", DEFAULT_W)
    height = canvas.get("height", DEFAULT_H)
    palette = merged_palette(spec, light_theme_defaults(spec))
    img = Image.new("RGBA", (c(width), c(height)), hex_rgba(palette["background"]))
    draw = ImageDraw.Draw(img)
    ex = Excal(width, height, background=palette["background"])
    margin = max(20, min(width, height) * 0.035)
    draw_rect(ex, draw, margin, margin, width - margin * 2, height - margin * 2, palette["border"], None, 2, 24)
    return ex, img, draw, palette, width, height, margin


def draw_light_title(ex, draw, spec, width, margin, palette):
    title = spec.get("title", {})
    main = title.get("main") or title.get("highlight") or title.get("prefix") or "Animated Diagram"
    subtitle = title.get("subtitle", "")
    draw_text(ex, draw, main, margin + 36, margin + 32, width - margin * 2 - 72, 44, 32, palette["text"], "center", bold=True, fit=True, min_size=18)
    if subtitle:
        draw_text(ex, draw, subtitle, margin + 36, margin + 78, width - margin * 2 - 72, 26, 17, palette["muted"], "center", fit=True, min_size=11)


def light_card(ex, draw, x, y, w, h, palette, title, body="", accent=None, index=None, item=None):
    colors = light_style_colors(palette, item, {"accent": accent or palette["primary"]})
    draw_rect(ex, draw, x, y, w, h, colors["stroke"], colors["fill"], 2, 14)
    if index is not None:
        draw_ellipse(ex, draw, x + 16, y + 18, 30, 30, colors["accent"], colors["accent"], 2)
        draw_text(ex, draw, str(index), x + 16, y + 18, 30, 30, 16, colors["index_text"], "center", bold=True, fit=True, min_size=10, wrap=False)
        text_x = x + 58
        text_w = w - 74
    else:
        text_x = x + 22
        text_w = w - 44
    draw_text(ex, draw, title, text_x, y + 17, text_w, 28, 20, colors["text"], "left", bold=True, fit=True, min_size=13)
    if body:
        draw_text(ex, draw, body, text_x, y + 50, text_w, h - 58, 14, colors["muted"], "left", fit=True, min_size=10)


def circular_geometry(spec, width, height):
    steps = spec.get("steps", [])
    n = max(1, len(steps))
    center = spec.get("center", {})
    cx = center.get("x", width / 2)
    cy = center.get("y", height * 0.34)
    radius = center.get("radius", min(width * 0.24, height * 0.24, 220))
    node_radius = center.get("node_radius", max(23, min(34, radius * 0.13)))
    positions = []
    for index in range(n):
        angle = -math.pi / 2 + math.tau * index / n
        positions.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), angle))
    return {
        "cx": cx,
        "cy": cy,
        "radius": radius,
        "node_radius": node_radius,
        "positions": positions,
    }


def draw_dashed_circle(ex, draw, cx, cy, radius, color, width=3, dash_degrees=10, gap_degrees=8):
    ex.ellipse(cx - radius, cy - radius, radius * 2, radius * 2, color, "transparent", width, "dashed")
    box = scaled_box(cx - radius, cy - radius, radius * 2, radius * 2)
    step = dash_degrees + gap_degrees
    for start in range(-90, 270, step):
        draw.arc(box, start=start, end=start + dash_degrees, fill=hex_rgba(color, 170), width=max(1, c(width)))


def draw_badge(ex, draw, text, x, y, palette, item=None):
    if not text:
        return
    colors = light_style_colors(
        palette,
        item,
        {"accent": palette["primary"], "fill": palette["primary_soft"], "stroke": palette["primary_soft"], "text": palette["primary"]},
    )
    font = load_font(14, cjk=has_cjk(text), bold=False)
    tw, _ = text_size(draw, text, font)
    width = max(46, tw / SCALE + 22)
    draw_rect(ex, draw, x, y, width, 27, colors["stroke"], colors["fill"], 1, 7)
    draw_text(ex, draw, text, x + 9, y + 4, width - 18, 18, 14, colors["accent"], "center", fit=True, min_size=10, wrap=False)


def draw_circular_loop_step_row(ex, draw, index, step, x, y, row_w, palette):
    number = str(index + 1)
    colors = light_style_colors(palette, step, {"accent": palette["primary"], "stroke": palette["primary"], "fill": palette["primary"]})
    draw_ellipse(ex, draw, x, y - 17, 32, 32, colors["stroke"], colors["fill"], 2)
    draw_text(ex, draw, number, x, y - 17, 32, 32, 17, colors["index_text"], "center", bold=True, fit=True, min_size=12, wrap=False)
    label = step.get("label", "")
    label_x = x + 48
    draw_text(ex, draw, label, label_x, y - 18, row_w - 160, 34, 21, colors["text"], "left", fit=True, min_size=13, wrap=True)
    label_font = load_font(21, cjk=has_cjk(label))
    label_width = min(text_size(draw, label, label_font)[0] / SCALE, row_w - 220)
    badge_x = min(label_x + label_width + 14, x + row_w - 130)
    draw_badge(ex, draw, step.get("badge", ""), badge_x, y - 14, palette, step)


def render_circular_loop(spec):
    canvas = spec.get("canvas", {})
    width = canvas.get("width", DEFAULT_W)
    height = canvas.get("height", DEFAULT_H)
    palette = merged_palette(spec, LIGHT_THEME)
    img = Image.new("RGBA", (c(width), c(height)), hex_rgba(palette["background"]))
    draw = ImageDraw.Draw(img)
    ex = Excal(width, height, background=palette["background"])

    margin = max(20, min(width, height) * 0.035)
    draw_rect(ex, draw, margin, margin, width - margin * 2, height - margin * 2, palette["border"], None, 2, 24)

    geom = circular_geometry(spec, width, height)
    cx, cy, radius = geom["cx"], geom["cy"], geom["radius"]
    node_r = geom["node_radius"]
    draw_dashed_circle(ex, draw, cx, cy, radius, palette["border"], 3)

    title = spec.get("title", {})
    main_title = title.get("main") or title.get("highlight") or title.get("prefix") or "Circular Loop"
    subtitle = title.get("subtitle", "")
    draw_text(ex, draw, main_title, cx - radius * 0.55, cy - 42, radius * 1.1, 44, 31, palette["text"], "center", bold=True, fit=True, min_size=18)
    draw_text(ex, draw, subtitle, cx - radius * 0.55, cy + 8, radius * 1.1, 28, 18, palette["muted"], "center", fit=True, min_size=12)

    steps = spec.get("steps", [])
    for index, (px, py, _) in enumerate(geom["positions"]):
        step = steps[index] if index < len(steps) else {}
        colors = light_style_colors(palette, step, {"accent": palette["primary"], "stroke": palette["primary"], "fill": palette["background"], "text": palette["primary"]})
        draw_ellipse(ex, draw, px - node_r, py - node_r, node_r * 2, node_r * 2, colors["stroke"], colors["fill"], 3)
        draw_text(ex, draw, str(index + 1), px - node_r, py - node_r, node_r * 2, node_r * 2, 22, colors["text"], "center", bold=True, fit=True, min_size=15, wrap=False)

    list_cfg = spec.get("legend", {})
    list_x = list_cfg.get("x", max(margin + 38, width * 0.07))
    list_y = list_cfg.get("y", max(cy + radius + 95, height * 0.64))
    row_gap = list_cfg.get("row_gap", min(49, max(38, (height - list_y - margin - 18) / max(1, len(steps)))))
    row_w = list_cfg.get("width", width - list_x - margin - 55)
    for index, step in enumerate(steps):
        draw_circular_loop_step_row(ex, draw, index, step, list_x, list_y + index * row_gap, row_w, palette)

    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_timeline(spec):
    ex, img, draw, palette, width, height, margin = light_canvas(spec)
    draw_light_title(ex, draw, spec, width, margin, palette)
    steps = spec.get("steps", spec.get("items", []))
    y = height * 0.42
    x1 = margin + 95
    x2 = width - margin - 95
    draw_line(ex, draw, [(x1, y), (x2, y)], palette["border"], 4)
    count = max(1, len(steps))
    gap = (x2 - x1) / max(1, count - 1)
    card_w = min(230, max(150, (x2 - x1) / max(1, count) + 32))
    for index, step in enumerate(steps):
        x = x1 + gap * index
        colors = light_style_colors(palette, step, {"accent": palette["primary"], "stroke": palette["primary"], "fill": palette["background"], "text": palette["primary"]})
        draw_ellipse(ex, draw, x - 22, y - 22, 44, 44, colors["stroke"], colors["fill"], 3)
        draw_text(ex, draw, str(index + 1), x - 22, y - 22, 44, 44, 20, colors["text"], "center", bold=True, fit=True, min_size=12, wrap=False)
        card_y = y + 58 if index % 2 == 0 else y - 138
        light_card(ex, draw, x - card_w / 2, card_y, card_w, 92, palette, step.get("label", ""), step.get("body", ""), index=index + 1, item=step)
    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_funnel(spec):
    ex, img, draw, palette, width, height, margin = light_canvas(spec)
    draw_light_title(ex, draw, spec, width, margin, palette)
    stages = spec.get("stages", spec.get("steps", []))
    count = max(1, len(stages))
    top_y = margin + 150
    row_h = min(92, max(62, (height - top_y - margin - 54) / count))
    max_w = width - margin * 2 - 160
    min_w = max_w * 0.42
    for index, stage in enumerate(stages):
        t = index / max(1, count - 1)
        w = max_w - (max_w - min_w) * t
        x = (width - w) / 2
        y = top_y + index * row_h
        fill = palette["primary_soft"] if index % 2 == 0 else palette["card"]
        colors = light_style_colors(palette, stage, {"accent": palette["primary"], "stroke": palette["primary"], "fill": fill, "value": palette["primary"]})
        draw_rect(ex, draw, x, y, w, row_h - 12, colors["stroke"], colors["fill"], 2, 16)
        label = stage.get("label", "")
        value = stage.get("value", "")
        draw_text(ex, draw, label, x + 26, y + 15, w * 0.55, row_h - 42, 22, colors["text"], "left", bold=True, fit=True, min_size=13)
        draw_text(ex, draw, value, x + w * 0.62, y + 15, w * 0.30, row_h - 42, 24, colors["value"], "right", bold=True, fit=True, min_size=13, wrap=False)
    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_matrix(spec):
    ex, img, draw, palette, width, height, margin = light_canvas(spec)
    draw_light_title(ex, draw, spec, width, margin, palette)
    left = margin + 120
    top = margin + 150
    chart_w = width - left - margin - 75
    chart_h = height - top - margin - 85
    draw_rect(ex, draw, left, top, chart_w, chart_h, palette["border"], palette["card"], 2, 14)
    draw_line(ex, draw, [(left + chart_w / 2, top), (left + chart_w / 2, top + chart_h)], palette["border"], 2, "dashed")
    draw_line(ex, draw, [(left, top + chart_h / 2), (left + chart_w, top + chart_h / 2)], palette["border"], 2, "dashed")
    draw_text(ex, draw, spec.get("x_axis", "Effort"), left + chart_w / 2 - 80, top + chart_h + 28, 160, 28, 16, palette["muted"], "center", fit=True, min_size=10)
    draw_text(ex, draw, spec.get("y_axis", "Impact"), left - 95, top + chart_h / 2 - 18, 80, 36, 16, palette["muted"], "center", fit=True, min_size=10)
    for item in spec.get("items", []):
        x = left + chart_w * max(0, min(1, item.get("x", 0.5)))
        y = top + chart_h * (1 - max(0, min(1, item.get("y", 0.5))))
        colors = light_style_colors(palette, item, {"accent": palette["primary"], "stroke": palette["primary"], "fill": palette["primary"]})
        draw_ellipse(ex, draw, x - 11, y - 11, 22, 22, colors["stroke"], colors["fill"], 2)
        draw_text(ex, draw, item.get("label", ""), x + 16, y - 18, 150, 34, 15, colors["text"], "left", fit=True, min_size=10)
    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_stack(spec):
    ex, img, draw, palette, width, height, margin = light_canvas(spec)
    draw_light_title(ex, draw, spec, width, margin, palette)
    layers = spec.get("layers", spec.get("steps", []))
    count = max(1, len(layers))
    stack_w = width - margin * 2 - 180
    stack_x = (width - stack_w) / 2
    row_h = min(86, max(58, (height - margin - 170) / count))
    start_y = margin + 145
    for index, layer in enumerate(layers):
        y = start_y + index * row_h
        inset = index * 18
        light_card(ex, draw, stack_x + inset, y, stack_w - inset * 2, row_h - 12, palette, layer.get("label", ""), layer.get("body", ""), index=index + 1, item=layer)
        if index < count - 1:
            mid_x = width / 2
            draw_line(ex, draw, [(mid_x, y + row_h - 12), (mid_x, y + row_h + 4)], palette["primary"], 2, "solid", True)
    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_before_after(spec):
    ex, img, draw, palette, width, height, margin = light_canvas(spec)
    draw_light_title(ex, draw, spec, width, margin, palette)
    before = spec.get("before", {})
    after = spec.get("after", {})
    col_gap = 82
    col_w = (width - margin * 2 - 120 - col_gap) / 2
    top = margin + 150
    h = height - top - margin - 46
    left_x = margin + 60
    right_x = left_x + col_w + col_gap
    for x, block, accent in [(left_x, before, palette["muted"]), (right_x, after, palette["primary"])]:
        colors = light_style_colors(palette, block, {"accent": accent, "stroke": accent, "fill": palette["card"]})
        draw_rect(ex, draw, x, top, col_w, h, colors["stroke"], colors["fill"], 2, 18)
        draw_text(ex, draw, block.get("title", ""), x + 26, top + 22, col_w - 52, 34, 25, colors["text"], "center", bold=True, fit=True, min_size=16)
        for index, item in enumerate(block.get("items", [])):
            row_y = top + 86 + index * 58
            draw_ellipse(ex, draw, x + 34, row_y + 4, 20, 20, colors["accent"], colors["accent"], 2)
            draw_text(ex, draw, str(index + 1), x + 34, row_y + 4, 20, 20, 12, palette["white"], "center", bold=True, fit=True, min_size=8, wrap=False)
            draw_text(ex, draw, item, x + 68, row_y - 2, col_w - 92, 34, 18, colors["text"], "left", fit=True, min_size=12)
    draw_line(ex, draw, [(left_x + col_w + 20, top + h / 2), (right_x - 20, top + h / 2)], palette["primary"], 3, "solid", True)
    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def render_static(spec):
    layout = layout_name(spec)
    if layout == "circular_loop":
        return render_circular_loop(spec)
    if layout == "timeline":
        return render_timeline(spec)
    if layout == "funnel":
        return render_funnel(spec)
    if layout == "matrix":
        return render_matrix(spec)
    if layout == "stack":
        return render_stack(spec)
    if layout == "before_after":
        return render_before_after(spec)

    width = spec.get("canvas", {}).get("width", DEFAULT_W)
    height = spec.get("canvas", {}).get("height", DEFAULT_H)
    ex = Excal(width, height)
    img = Image.new("RGBA", (width * SCALE, height * SCALE), hex_rgba(THEME["bg"]))
    draw = ImageDraw.Draw(img)

    title = spec.get("title", {})
    draw_line(ex, draw, [(29, 31), (29, 78)], THEME["purple"], 11)
    draw_text(ex, draw, title.get("prefix", "The internals of"), 45, 14, 535, 66, 47, THEME["white"], "left", hand=True, bold=True)
    draw_rect(ex, draw, 600, 27, 392, 72, THEME["highlight"], THEME["highlight"], 2, 16)
    draw_text(ex, draw, title.get("highlight", "Memory Pack"), 622, 19, 350, 76, 44, THEME["green"], "center", hand=True, bold=True)
    draw_text(ex, draw, title.get("subtitle", ""), 104, 90, 420, 25, 15, THEME["muted"], "left")

    draw_rect(ex, draw, 18, 117, 1174, 994, THEME["frame"], None, 2, 29)
    brand(ex, draw, spec.get("signature", "@岚叔"))

    inputs = spec.get("inputs", [])
    while len(inputs) < 4:
        inputs.append({"label": "", "icon": "file"})
    draw_rect(ex, draw, 389, 138, 430, 101, THEME["green"], None, 2, 8)
    draw_text(ex, draw, spec.get("input_title", "Source / Input"), 498, 144, 210, 31, 22, THEME["white"], "center", hand=True, bold=True)
    for x, item in zip([423, 532, 640, 748], inputs[:4]):
        small_input(ex, draw, x, 180, item)
    draw_line(ex, draw, [(605, 239), (605, 316)], THEME["white"], 2, "solid", True)

    core = spec.get("core", {})
    cards = core.get("cards", [])
    while len(cards) < 3:
        cards.append({"title": "", "body": "", "icon": "file"})
    draw_rect(ex, draw, 53, 317, 1104, 320, THEME["core_stroke"], THEME["core_fill"], 2, 20)
    draw_text(ex, draw, core.get("title", "Archive Core"), 462, 327, 210, 31, 22, THEME["white"], "center", hand=True, bold=True)
    draw_text(ex, draw, core.get("subtitle", "(local read-only pipeline)"), 635, 336, 220, 23, 13, THEME["white"], "center")
    core_card(ex, draw, 95, 366, cards[0])
    core_card(ex, draw, 472, 366, cards[1])
    core_card(ex, draw, 850, 366, cards[2])
    draw_line(ex, draw, [(355, 411), (472, 411)], THEME["white"], 2, "solid", True)
    draw_line(ex, draw, [(732, 411), (850, 411)], THEME["white"], 2, "solid", True)
    draw_line(ex, draw, [(982, 456), (982, 481), (768, 481), (768, 508)], THEME["white"], 2, "solid", True)

    decision = spec.get("decision", {"title": "Ready?", "body": "safe, traced\nusable"})
    draw_diamond(ex, draw, 706, 508, 120, 120, THEME["green"], "#052515", 2)
    draw_text(ex, draw, decision.get("title", "Ready?"), 728, 541, 78, 26, 20, THEME["white"], "center", fit=True, min_size=14)
    draw_text(ex, draw, decision.get("body", ""), 728, 569, 78, 34, 14, THEME["white"], "center", fit=True, min_size=10)
    draw_rect(ex, draw, 1022, 527, 100, 94, THEME["core_stroke"], THEME["blue_fill"], 2, 9)
    icon(ex, draw, spec.get("output", {}).get("icon", "file"), 1035, 537, THEME["cyan"])
    draw_text(ex, draw, spec.get("output", {}).get("label", "Report"), 1038, 588, 70, 24, 18, THEME["white"], "center", bold=True, fit=True, min_size=12)
    draw_line(ex, draw, [(826, 568), (1022, 568)], THEME["white"], 2, "solid", True)
    draw_text(ex, draw, "Yes", 900, 543, 45, 25, 15, THEME["white"], "center")
    draw_line(ex, draw, [(707, 568), (510, 568), (222, 568), (222, 456)], THEME["muted"], 2, "dashed", True)
    draw_text(ex, draw, spec.get("loop_label", "Loop until checked and updated"), 330, 504, 540, 25, 14, THEME["white"], "center")
    draw_text(ex, draw, spec.get("retry_label", "No / missing source or conflict"), 475, 580, 250, 24, 14, THEME["white"], "center")

    draw_line(ex, draw, [(156, 637), (156, 736)], THEME["white"], 2, "solid", True)
    draw_line(ex, draw, [(205, 736), (205, 637)], THEME["white"], 2, "solid", True)
    draw_text(ex, draw, "Read", 109, 677, 45, 22, 16, THEME["white"], "center")
    draw_text(ex, draw, "Context", 211, 676, 70, 22, 16, THEME["white"], "center")

    left = spec.get("left_panel", {})
    draw_rect(ex, draw, 39, 735, 281, 344, THEME["green"], THEME["source_fill"], 2, 14)
    draw_text(ex, draw, left.get("title", "Memory Sources"), 58, 752, 180, 30, 22, THEME["white"], "left", hand=True, bold=True)
    draw_text(ex, draw, left.get("badge", "read only"), 244, 779, 62, 18, 11, THEME["green"], "center")
    for (y, h), card in zip([(797, 78), (892, 78), (987, 62)], left.get("cards", [])[:3]):
        mini_card(ex, draw, 51, y, 258, h, card, THEME["green"], "#04200f")

    center = spec.get("center_panel", {})
    draw_rect(ex, draw, 333, 734, 522, 346, THEME["purple"], THEME["archive_fill"], 2, 14)
    draw_text(ex, draw, center.get("title", "Archive Layers"), 512, 756, 180, 34, 23, THEME["white"], "center", hand=True, bold=True)
    draw_text(ex, draw, center.get("subtitle", "(local, readable, traceable storage)"), 444, 790, 300, 24, 14, THEME["white"], "center")
    layer_cards = center.get("cards", [])[:4]
    while len(layer_cards) < 4:
        layer_cards.append({"title": "", "body": "", "icon": "file"})
    for x, card in zip([346, 486, 626, 766], layer_cards):
        draw_rect(ex, draw, x, 827, 112, 142, THEME["purple"], "#17091d", 2, 8)
        icon(ex, draw, card.get("icon", "file"), x + 18, 840, card.get("color", THEME["cyan"]))
        draw_text(ex, draw, card.get("title", ""), x + 10, 910, 92, 25, 18, THEME["white"], "center", bold=True, fit=True, min_size=12)
        draw_text(ex, draw, card.get("body", ""), x + 8, 936, 96, 28, 11, THEME["white"], "center", spacing=2, fit=True, min_size=8)
    draw_line(ex, draw, [(458, 890), (486, 890)], THEME["white"], 2, "solid", True)
    draw_line(ex, draw, [(598, 890), (626, 890)], THEME["white"], 2, "solid", True)
    draw_line(ex, draw, [(738, 890), (766, 890)], THEME["white"], 2, "solid", True)
    draw_rect(ex, draw, 491, 1010, 220, 50, THEME["purple"], THEME["archive_fill"], 2, 8)
    draw_text(ex, draw, center.get("footer", "Redact + Dedup"), 528, 1017, 165, 33, 20, THEME["white"], "center", hand=True, bold=True, fit=True, min_size=14)
    draw_line(ex, draw, [(603, 969), (603, 1010)], THEME["muted"], 2, "dashed", True)

    right = spec.get("right_panel", {})
    draw_line(ex, draw, [(855, 890), (904, 890)], THEME["white"], 2, "solid", True)
    draw_text(ex, draw, right.get("incoming_label", "Compile"), 850, 868, 65, 20, 12, THEME["white"], "center")
    draw_rect(ex, draw, 904, 735, 258, 344, THEME["green"], THEME["pack_fill"], 2, 14)
    draw_text(ex, draw, right.get("title", "Memory Pack"), 948, 750, 170, 34, 22, THEME["white"], "center", hand=True, bold=True)
    for y, card in zip([786, 884, 982], right.get("cards", [])[:3]):
        pack_row(ex, draw, 918, y, card)
    draw_line(ex, draw, [(1036, 735), (1036, 691), (766, 691), (766, 628)], THEME["white"], 2, "solid", True)
    draw_text(ex, draw, right.get("return_label", "Reusable"), 867, 669, 75, 23, 16, THEME["white"], "center")

    for x, y, color in [(375, 292, THEME["cyan"]), (704, 293, THEME["green"]), (1048, 292, THEME["purple"]), (315, 707, THEME["green"]), (868, 707, THEME["purple"])]:
        draw_line(ex, draw, [(x - 8, y), (x + 8, y)], color, 2)
        draw_line(ex, draw, [(x, y - 8), (x, y + 8)], color, 2)

    return ex, img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")


def finish_options(spec):
    dark_default = layout_name(spec) == "architecture" or style_tone(spec) == "dark_technical"
    options = {
        "grain": True,
        "vignette": dark_default,
        "soft_glow": dark_default,
    }
    options.update(spec.get("finish", {}))
    return {key: bool(options[key]) for key in ("grain", "vignette", "soft_glow")}


def apply_soft_glow(img, rects):
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for rect, color, line_width, radius in rects:
        g.rounded_rectangle(rect, radius=radius, outline=hex_rgba(color, 70), width=line_width)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))


def apply_grain(img, light=True):
    width, height = img.size
    grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    rng = random.Random(2069769416930414980)
    count = max(600, width * height // 420) if light else 2600
    low, high = (180, 255) if light else (120, 220)
    for _ in range(count):
        x = rng.randrange(width)
        y = rng.randrange(height)
        tone = rng.randrange(low, high)
        gd.point((x, y), fill=(tone, tone, tone, rng.randrange(4, 14 if not light else 12)))
    img.alpha_composite(grain)


def apply_vignette(img):
    width, height = img.size
    mask_small = Image.new("L", (180, 170), 0)
    pixels = []
    cx, cy = 90, 78
    max_dist = math.dist((0, 0), (cx, cy))
    for y in range(170):
        for x in range(180):
            dist = math.dist((x, y), (cx, cy)) / max_dist
            pixels.append(int(max(0, min(115, (dist - 0.38) * 150))))
    mask_small.putdata(pixels)
    mask = mask_small.resize((width, height), Image.Resampling.BICUBIC)
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vignette.putalpha(mask)
    img.alpha_composite(vignette)


def premium_finish(base, spec=None):
    spec = spec or {"layout": "architecture"}
    options = finish_options(spec)
    width, height = base.size
    img = base.convert("RGBA")
    if options["soft_glow"]:
        apply_soft_glow(
            img,
            [
                ((18, 117, 1192, 1111), THEME["frame"], 3, 18),
                ((53, 317, 1157, 637), THEME["core_stroke"], 3, 18),
                ((333, 734, 855, 1080), THEME["purple"], 3, 18),
                ((39, 735, 320, 1079), THEME["green"], 3, 18),
                ((904, 735, 1162, 1079), THEME["green"], 3, 18),
                ((600, 27, 992, 99), THEME["green"], 2, 18),
            ],
        )
    if options["grain"]:
        apply_grain(img, light=False)
    if options["vignette"]:
        apply_vignette(img)
    return img.convert("RGB")


def light_finish(base, spec):
    width, height = base.size
    img = base.convert("RGBA")
    options = finish_options(spec)
    palette = merged_palette(spec, light_theme_defaults(spec))
    if options["soft_glow"]:
        margin = max(20, min(width, height) * 0.035)
        apply_soft_glow(
            img,
            [
                ((margin, margin, width - margin, height - margin), palette["border"], 2, 24),
                ((margin + 80, height * 0.38, width - margin - 80, height * 0.46), palette["primary"], 2, 18),
            ],
        )
    if options["grain"]:
        apply_grain(img, light=style_tone(spec) != "dark_technical")
    if options["vignette"]:
        apply_vignette(img)
    return img.convert("RGB")


def finish_static(spec, static):
    if is_light_layout(spec):
        return light_finish(static, spec)
    return premium_finish(static, spec)


def draw_glow_dot(draw, x, y, color, strength=1.0):
    for radius, alpha in [(15, 42), (10, 70), (5, 210)]:
        a = int(alpha * strength)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=hex_rgba(color, a))
    draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=hex_rgba(THEME["white"], 245))


def pulse_rect(draw, rect, color, phase, radius=10):
    x1, y1, x2, y2 = rect
    alpha = int(70 + 70 * (0.5 + 0.5 * math.sin(phase)))
    for grow, width in [(0, 2), (4, 2), (8, 1)]:
        draw.rounded_rectangle((x1 - grow, y1 - grow, x2 + grow, y2 + grow), radius=radius + grow, outline=hex_rgba(color, max(25, alpha - grow * 8)), width=width)


def draw_light_glow_dot(draw, x, y, color, strength=1.0):
    for radius, alpha in [(24, 45), (15, 72), (7, 190)]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=hex_rgba(color, int(alpha * strength)))
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=hex_rgba(color, 245))


def draw_light_arrow_marker(draw, x, y, color, strength=1.0):
    alpha = int(230 * strength)
    shaft = 34
    head = 12
    width = max(1, int(round(3 * strength)))
    start = (x - shaft / 2, y)
    end = (x + shaft / 2, y)
    draw.line([start, end], fill=hex_rgba(color, alpha), width=width)
    p1 = (end[0] - head, end[1] - head * 0.58)
    p2 = (end[0] - head, end[1] + head * 0.58)
    draw.line([p1, end, p2], fill=hex_rgba(color, alpha), width=width)


def animate_circular_loop_frame(base, spec, idx, total):
    frame = base.convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = frame.size
    palette = merged_palette(spec, LIGHT_THEME)
    geom = circular_geometry(spec, width, height)
    steps = spec.get("steps", [])
    n = max(1, len(steps))
    progress = idx / total
    angle = -math.pi / 2 + math.tau * progress
    x = geom["cx"] + geom["radius"] * math.cos(angle)
    y = geom["cy"] + geom["radius"] * math.sin(angle)
    for trail, strength in [(0, 1.0), (-0.035, 0.62), (-0.07, 0.34)]:
        trail_angle = -math.pi / 2 + math.tau * ((progress + trail) % 1.0)
        tx = geom["cx"] + geom["radius"] * math.cos(trail_angle)
        ty = geom["cy"] + geom["radius"] * math.sin(trail_angle)
        draw_light_glow_dot(draw, tx, ty, palette["primary"], strength)
    active = int(progress * n) % n
    if steps:
        node_x, node_y, _ = geom["positions"][active]
        pulse_rect(draw, (node_x - geom["node_radius"], node_y - geom["node_radius"], node_x + geom["node_radius"], node_y + geom["node_radius"]), palette["primary"], progress * math.tau * 3, radius=int(geom["node_radius"]))
        margin = max(20, min(width, height) * 0.035)
        list_cfg = spec.get("legend", {})
        list_x = list_cfg.get("x", max(margin + 38, width * 0.07))
        list_y = list_cfg.get("y", max(geom["cy"] + geom["radius"] + 95, height * 0.64))
        row_gap = list_cfg.get("row_gap", min(49, max(38, (height - list_y - margin - 18) / max(1, len(steps)))))
        row_w = list_cfg.get("width", width - list_x - margin - 55)
        row_y = list_y + active * row_gap
        draw.rounded_rectangle(
            (list_x - 12, row_y - 23, list_x + row_w, row_y + 22),
            radius=13,
            fill=hex_rgba(palette["primary_soft"], 105),
            outline=hex_rgba(palette["primary"], 70),
            width=1,
        )
    draw_light_glow_dot(draw, x, y, palette["primary"], 1.0)
    frame.alpha_composite(overlay)
    return frame.convert("RGB")


def light_pulse_targets(spec, width, height):
    layout = layout_name(spec)
    margin = max(20, min(width, height) * 0.035)
    if layout == "timeline":
        steps = spec.get("steps", spec.get("items", []))
        y = height * 0.42
        x1 = margin + 95
        x2 = width - margin - 95
        count = max(1, len(steps))
        gap = (x2 - x1) / max(1, count - 1)
        return [(x1 + gap * i - 28, y - 28, x1 + gap * i + 28, y + 28) for i in range(count)]
    if layout == "funnel":
        stages = spec.get("stages", spec.get("steps", []))
        count = max(1, len(stages))
        top_y = margin + 150
        row_h = min(92, max(62, (height - top_y - margin - 54) / count))
        max_w = width - margin * 2 - 160
        min_w = max_w * 0.42
        targets = []
        for i in range(count):
            t = i / max(1, count - 1)
            w = max_w - (max_w - min_w) * t
            x = (width - w) / 2
            y = top_y + i * row_h
            targets.append((x, y, x + w, y + row_h - 12))
        return targets
    if layout == "matrix":
        items = spec.get("items", [])
        left = margin + 120
        top = margin + 150
        chart_w = width - left - margin - 75
        chart_h = height - top - margin - 85
        targets = []
        for item in items:
            x = left + chart_w * max(0, min(1, item.get("x", 0.5)))
            y = top + chart_h * (1 - max(0, min(1, item.get("y", 0.5))))
            targets.append((x - 22, y - 22, x + 22, y + 22))
        return targets
    if layout == "stack":
        layers = spec.get("layers", spec.get("steps", []))
        count = max(1, len(layers))
        stack_w = width - margin * 2 - 180
        stack_x = (width - stack_w) / 2
        row_h = min(86, max(58, (height - margin - 170) / count))
        start_y = margin + 145
        return [(stack_x + i * 18, start_y + i * row_h, stack_x + stack_w - i * 18, start_y + i * row_h + row_h - 12) for i in range(count)]
    if layout == "before_after":
        col_gap = 82
        col_w = (width - margin * 2 - 120 - col_gap) / 2
        top = margin + 150
        h = height - top - margin - 46
        left_x = margin + 60
        right_x = left_x + col_w + col_gap
        return [(left_x, top, left_x + col_w, top + h), (right_x, top, right_x + col_w, top + h)]
    return []


def animate_light_layout_frame(base, spec, idx, total):
    frame = base.convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = frame.size
    palette = merged_palette(spec, LIGHT_THEME)
    progress = idx / total
    margin = max(20, min(width, height) * 0.035)
    path_y = height * 0.42 if layout_name(spec) == "timeline" else height * 0.5
    path = [(margin + 70, path_y), (width - margin - 70, path_y)]
    animation = spec.get("animation", {})
    marker = animation.get("marker", "dot")
    for trail, strength in [(0, 1.0), (-0.045, 0.60), (-0.09, 0.32)]:
        x, y = point_at_fraction(path, progress + trail)
        if marker == "arrow":
            draw_light_arrow_marker(draw, x, y, palette["primary"], strength)
        else:
            draw_light_glow_dot(draw, x, y, palette["primary"], strength)
    targets = light_pulse_targets(spec, width, height)
    if targets:
        active = int(progress * len(targets)) % len(targets)
        pulse_rect(draw, targets[active], palette["primary"], progress * math.tau * 3, radius=16)
    frame.alpha_composite(overlay)
    return frame.convert("RGB")


def animate_frame(base, idx, total, spec=None):
    if spec and layout_name(spec) == "circular_loop":
        return animate_circular_loop_frame(base, spec, idx, total)
    if spec and is_light_layout(spec):
        return animate_light_layout_frame(base, spec, idx, total)

    frame = base.convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    progress = idx / total
    paths = [
        ([(605, 239), (605, 316)], THEME["green"], 0.00),
        ([(355, 411), (472, 411)], THEME["cyan"], 0.10),
        ([(732, 411), (850, 411)], THEME["cyan"], 0.24),
        ([(982, 456), (982, 481), (768, 481), (768, 508)], THEME["core_stroke"], 0.38),
        ([(826, 568), (1022, 568)], THEME["green"], 0.54),
        ([(707, 568), (510, 568), (222, 568), (222, 456)], THEME["purple"], 0.66),
        ([(156, 637), (156, 736)], THEME["green"], 0.18),
        ([(205, 736), (205, 637)], THEME["green"], 0.58),
        ([(458, 890), (486, 890), (598, 890), (626, 890), (738, 890), (766, 890)], THEME["purple"], 0.32),
        ([(855, 890), (904, 890)], THEME["white"], 0.46),
        ([(1036, 735), (1036, 691), (766, 691), (766, 628)], THEME["amber"], 0.72),
    ]
    for points, color, offset in paths:
        for trail, strength in [(0, 1.0), (-0.035, 0.72), (-0.07, 0.44)]:
            x, y = point_at_fraction(points, progress + offset + trail)
            draw_glow_dot(draw, x, y, color, strength)
    pulse_targets = [
        ((389, 138, 819, 239), THEME["green"]),
        ((95, 366, 355, 456), THEME["core_stroke"]),
        ((472, 366, 732, 456), THEME["green"]),
        ((850, 366, 1110, 456), THEME["core_stroke"]),
        ((706, 508, 826, 628), THEME["green"]),
        ((333, 734, 855, 1080), THEME["purple"]),
        ((904, 735, 1162, 1079), THEME["green"]),
    ]
    active = (idx // 6) % len(pulse_targets)
    for pos, (rect, color) in enumerate(pulse_targets):
        if pos == active:
            pulse_rect(draw, rect, color, progress * math.tau * 2, 12)
    frame.alpha_composite(overlay)
    return frame.convert("RGB")


def write_outputs(spec, outdir, basename):
    outdir.mkdir(parents=True, exist_ok=True)
    ex, static = render_static(spec)
    final = finish_static(spec, static)
    png_path = outdir / f"{basename}.png"
    gif_path = outdir / f"{basename}.gif"
    excalidraw_path = outdir / f"{basename}.excalidraw"
    final.save(png_path, "PNG")
    frames = [animate_frame(final, i, spec.get("canvas", {}).get("frames", DEFAULT_FRAMES), spec) for i in range(spec.get("canvas", {}).get("frames", DEFAULT_FRAMES))]
    duration = int(1000 / spec.get("canvas", {}).get("fps", DEFAULT_FPS))
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=duration, loop=0, optimize=False)
    ex.write(excalidraw_path)
    return {"png": str(png_path), "gif": str(gif_path), "excalidraw": str(excalidraw_path), "elements": len(ex.elements)}


def frame_diff_report(gif_path):
    with Image.open(gif_path) as im:
        picks = [0, max(1, im.n_frames // 4), max(2, im.n_frames // 2), max(3, 3 * im.n_frames // 4), im.n_frames - 1]
        frames = []
        for idx in picks:
            im.seek(idx)
            frames.append(im.convert("RGB"))
        frame_count = im.n_frames
    diffs = []
    for left, right, a, b in zip(frames, frames[1:], picks, picks[1:]):
        diff = ImageChops.difference(left, right)
        bbox = diff.getbbox()
        changed = 0
        if bbox:
            cropped = diff.crop(bbox)
            data = cropped.get_flattened_data() if hasattr(cropped, "get_flattened_data") else cropped.getdata()
            changed = sum(1 for px in data if px != (0, 0, 0))
        diffs.append({"from": a, "to": b, "changed_pixels": changed})
    return {"frames": frame_count, "diffs": diffs}


def element_bbox(element):
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    return (
        x,
        y,
        x + float(element.get("width", 0)),
        y + float(element.get("height", 0)),
    )


def readability_checks(excalidraw, spec, expected_width, expected_height):
    layout = layout_name(spec)
    min_font = 8 if layout == "architecture" else spec.get("quality", {}).get("min_font_size", 8)
    text_elements = [element for element in excalidraw.get("elements", []) if element.get("type") == "text"]
    boxes = [element_bbox(element) for element in text_elements]
    return [
        {
            "name": "readability_min_font_size",
            "ok": all(int(element.get("fontSize", 0)) >= min_font for element in text_elements),
            "min_font": min_font,
        },
        {
            "name": "readability_text_within_canvas",
            "ok": all(0 <= box[0] and 0 <= box[1] and box[2] <= expected_width and box[3] <= expected_height for box in boxes),
        },
    ]


def check_outputs(result, spec):
    canvas = spec.get("canvas", {})
    expected_width = canvas.get("width", DEFAULT_W)
    expected_height = canvas.get("height", DEFAULT_H)
    expected_frames = canvas.get("frames", DEFAULT_FRAMES)
    expected_fps = canvas.get("fps", DEFAULT_FPS)

    checks = []

    gif_path = Path(result["gif"])
    with Image.open(gif_path) as gif:
        gif_width = gif.width
        gif_height = gif.height
        gif_frames = gif.n_frames
        duration_ms = gif.info.get("duration")
    actual_fps = round(1000 / duration_ms, 3) if duration_ms else None
    checks.extend(
        [
            {"name": "gif_exists", "ok": gif_path.is_file()},
            {"name": "gif_width", "ok": gif_width == expected_width, "expected": expected_width, "actual": gif_width},
            {"name": "gif_height", "ok": gif_height == expected_height, "expected": expected_height, "actual": gif_height},
            {"name": "gif_frames", "ok": gif_frames == expected_frames, "expected": expected_frames, "actual": gif_frames},
            {"name": "gif_fps", "ok": duration_ms == int(1000 / expected_fps), "expected": expected_fps, "actual": actual_fps},
        ]
    )

    diff_report = frame_diff_report(gif_path)
    checks.append(
        {
            "name": "gif_has_motion",
            "ok": any(item["changed_pixels"] > 0 for item in diff_report["diffs"]),
            "diffs": diff_report["diffs"],
        }
    )

    excalidraw_path = Path(result["excalidraw"])
    excalidraw = json.loads(excalidraw_path.read_text(encoding="utf-8"))
    elements = excalidraw.get("elements", [])
    ids = [element.get("id") for element in elements]
    text_elements = [element for element in elements if element.get("type") == "text"]
    checks.extend(
        [
            {"name": "excalidraw_exists", "ok": excalidraw_path.is_file()},
            {"name": "excalidraw_unique_ids", "ok": len(ids) == len(set(ids))},
            {"name": "excalidraw_text_font_family", "ok": all(element.get("fontFamily") == 5 for element in text_elements)},
            {"name": "excalidraw_files_empty", "ok": excalidraw.get("files") == {}},
        ]
    )
    checks.extend(readability_checks(excalidraw, spec, expected_width, expected_height))

    png_path = Path(result["png"])
    with Image.open(png_path) as png:
        png_width = png.width
        png_height = png.height
    checks.extend(
        [
            {"name": "png_exists", "ok": png_path.is_file()},
            {"name": "png_width", "ok": png_width == expected_width, "expected": expected_width, "actual": png_width},
            {"name": "png_height", "ok": png_height == expected_height, "expected": expected_height, "actual": png_height},
        ]
    )

    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="Render a premium hand-drawn animated diagram from a JSON spec.")
    parser.add_argument("--spec", required=True, help="Path to spec JSON.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    parser.add_argument("--basename", default="animated-diagram", help="Output basename.")
    parser.add_argument("--verify", action="store_true", help="Print frame-diff verification after rendering.")
    parser.add_argument("--check", action="store_true", help="Validate PNG, GIF, and Excalidraw output contracts; exits nonzero on failure.")
    args = parser.parse_args()

    raw_spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    spec = normalize_render_input(raw_spec)
    result = write_outputs(spec, Path(args.outdir), args.basename)
    if args.verify:
        result["verification"] = frame_diff_report(result["gif"])
    if args.check:
        result["checks"] = check_outputs(result, spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check and not result["checks"]["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
