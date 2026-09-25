"""Small package-level check for the prototype's SVG, data, and formula contracts."""
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
EXPECTED = {"業務員": 120, "銀保": 88, "經代": 54, "直效": 38}
RATIO = 960 / 420
NSMAP = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
}


def package(path, prefixes):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        content = {name: archive.read(name) for name in names if name.endswith((".xml", ".rels"))}
    svg = [name for name in names if name.endswith(".svg")]
    png = [name for name in names if name.endswith(".png")]
    rels = [name for name, value in content.items() if b".svg" in value or b"image/svg+xml" in value]
    text = b"\n".join(content.values()).decode("utf-8", "ignore")
    return {"path": str(path), "svg_parts": svg, "png_fallback_parts": png, "svg_relationship_parts": rels, "contains_all_data_labels": all(label in text for label in EXPECTED)}


def aspect_ratios(path, kind):
    with zipfile.ZipFile(path) as archive:
        if kind == "pptx":
            roots = [ET.fromstring(archive.read(f"ppt/slides/slide{number}.xml")) for number in (1, 2)]
            extents = [root.find(".//p:pic/p:spPr/a:xfrm/a:ext", NSMAP) for root in roots]
        elif kind == "docx":
            root = ET.fromstring(archive.read("word/document.xml"))
            extents = root.findall(".//wp:inline/wp:extent", NSMAP)
        else:
            root = ET.fromstring(archive.read("xl/drawings/drawing1.xml"))
            extents = root.findall(".//xdr:oneCellAnchor/xdr:ext", NSMAP)
    raw_ratios = [int(extent.get("cx")) / int(extent.get("cy")) for extent in extents]
    if len(raw_ratios) != 2 or any(abs(ratio - RATIO) > 0.00001 for ratio in raw_ratios):
        raise ValueError(f"{kind} image aspect ratio mismatch: {raw_ratios}")
    return [round(ratio, 6) for ratio in raw_ratios]


def reader_copy_is_clean():
    prohibited = ("SVG 優先", "資料與文字可重製", "原圖保留，周邊文字與資料可編輯")
    targets = {
        OUTPUT / "transglobe-prototype.pptx": ("ppt/slides/slide1.xml", "ppt/slides/slide2.xml"),
        OUTPUT / "transglobe-prototype.docx": ("word/document.xml",),
        OUTPUT / "transglobe-prototype.xlsx": ("xl/worksheets/sheet1.xml",),
    }
    for path, names in targets.items():
        with zipfile.ZipFile(path) as archive:
            text = "\n".join(archive.read(name).decode("utf-8", "ignore") for name in names)
        if any(phrase in text for phrase in prohibited):
            return False
    return True


def docx_retains_native_copy():
    source = json.loads((ROOT / "data.json").read_text())
    required = [source["title_before"], source["title_after"], source["period"], *source["paragraphs"]]
    with zipfile.ZipFile(OUTPUT / "transglobe-prototype.docx") as archive:
        document = archive.read("word/document.xml").decode("utf-8", "ignore")
    return all(text in document for text in required) and document.count("<wp:inline") == 2 and document.count('w:type="page"') == 1


def font_contracts_hold():
    with zipfile.ZipFile(OUTPUT / "transglobe-prototype.docx") as archive:
        document = archive.read("word/document.xml").decode("utf-8", "ignore")
    with zipfile.ZipFile(OUTPUT / "transglobe-prototype.xlsx") as archive:
        styles = archive.read("xl/styles.xml").decode("utf-8", "ignore")
    return {
        "docx_title": all(value in document for value in ('w:ascii="Cambria"', 'w:hAnsi="Cambria"', 'w:eastAsia="PMingLiU"')),
        "xlsx_cells": "Microsoft JhengHei" in styles,
    }


def main():
    pptx = package(OUTPUT / "transglobe-prototype.pptx", ["ppt/"])
    docx = package(OUTPUT / "transglobe-prototype.docx", ["word/"])
    xlsx = package(OUTPUT / "transglobe-prototype.xlsx", ["xl/"])
    with zipfile.ZipFile(OUTPUT / "transglobe-prototype.xlsx") as archive:
        formulas = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
    xlsx["sum_formula_preserved"] = "SUM(B2:B5)" in formulas
    aspect = {
        "source_svg": round(RATIO, 6),
        "pptx": aspect_ratios(OUTPUT / "transglobe-prototype.pptx", "pptx"),
        "docx": aspect_ratios(OUTPUT / "transglobe-prototype.docx", "docx"),
        "xlsx": aspect_ratios(OUTPUT / "transglobe-prototype.xlsx", "xlsx"),
    }
    fonts = font_contracts_hold()
    report = {
        "purpose": "Package check only. It does not prove rendering in Office applications.",
        "svg_priority": {"pptx": pptx, "docx": docx, "xlsx": xlsx},
        "png_fallback_used": any(item["png_fallback_parts"] for item in (pptx, docx, xlsx)),
        "svg_image_aspect_ratio": aspect,
        "reader_copy_has_no_authoring_notes": reader_copy_is_clean(),
        "docx_retains_titles_period_and_body": docx_retains_native_copy(),
        "font_contracts": fonts,
        "data": {"unit": "百萬元", "illustrative": True, "channels": EXPECTED, "total": 300},
        "result": "pass" if all(len(item["svg_parts"]) >= 2 and item["svg_relationship_parts"] and item["contains_all_data_labels"] for item in (pptx, docx, xlsx)) and xlsx["sum_formula_preserved"] and reader_copy_is_clean() and docx_retains_native_copy() and all(fonts.values()) else "fail",
    }
    target = ROOT / "office-checks.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["result"] != "pass":
        raise SystemExit(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
