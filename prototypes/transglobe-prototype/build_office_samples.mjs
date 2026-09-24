import fs from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const artifactRequire = createRequire(new URL("./.build/runtime.cjs", import.meta.url));
const { Presentation, PresentationFile, SpreadsheetFile, Workbook } = artifactRequire("@oai/artifact-tool");

const run = promisify(execFile);
const root = path.resolve("prototypes/transglobe-prototype");
const assets = path.join(root, "assets");
const output = path.join(root, "output");
const build = path.join(root, ".build");
const skillDir = "/Users/isaacyslin/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const python = process.env.RUNTIME_PYTHON ?? "/Users/isaacyslin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const colors = { title: "#000099", focus: "#28317B", compare: "#7F7F7F", body: "#111111", secondary: "#4A4A4A" };

const required = ["chart-before.svg", "chart-after.svg"];
for (const filename of required) {
  try { await fs.access(path.join(assets, filename)); }
  catch { throw new Error(`Missing ${path.join(assets, filename)}`); }
}

const source = JSON.parse(await fs.readFile(path.join(root, "data.json"), "utf8"));
const channels = Array.isArray(source) ? source : (source.channels ?? source.rows);
if (!Array.isArray(channels) || channels.length !== 4) throw new Error("data.json must contain four channels");
const rows = channels.map(({ name, channel, value, amount }) => [name ?? channel, Number(value ?? amount)]);
if (rows.some(([name, value]) => !name || !Number.isFinite(value))) throw new Error("Each channel needs a name and numeric value");
if (rows.reduce((sum, [, value]) => sum + value, 0) !== 300) throw new Error("Illustrative data must total 300");
const beforeSvg = await fs.readFile(path.join(assets, "chart-before.svg"), "utf8");
const afterSvg = await fs.readFile(path.join(assets, "chart-after.svg"), "utf8");
const titles = [source.title_before ?? "通路保費組成", source.title_after ?? "通路保費組成"];
const period = source.period ?? "同一期間";
const sourceNote = source.source ?? "校準用示意資料";
await fs.mkdir(build, { recursive: true });
await fs.mkdir(output, { recursive: true });

const text = (slide, value, x, y, w, h, size, color = colors.body, bold = false) => {
  const box = slide.shapes.add({ geometry: "textbox", position: { left: x, top: y, width: w, height: h }, fill: "none", line: { fill: "none", width: 0 } });
  box.text = value;
  box.text.style = { typeface: "Microsoft JhengHei", fontSize: size, bold, color, autoFit: "shrinkText" };
  return box;
};

async function createPptx() {
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  for (const [label, svg, accent, title] of [
    ["Before", beforeSvg, colors.compare, titles[0]],
    ["After", afterSvg, colors.focus, titles[1]],
  ]) {
    const slide = presentation.slides.add();
    slide.background.fill = "#FFFFFF";
    text(slide, title, 72, 42, 1000, 56, 36, colors.title, true);
    text(slide, label, 1100, 54, 108, 28, 16, accent, true);
    text(slide, period, 72, 108, 520, 36, 24, colors.secondary);
    slide.images.add({ svg, alt: `${label} 通路保費組成圖`, fit: "contain", position: { left: 160, top: 160, width: 960, height: 420 } });
    text(slide, `資料來源：${sourceNote}`, 72, 620, 1080, 28, 16, colors.secondary);
    text(slide, `${rows.map(([name, value]) => `${name} ${value}`).join("  ")}　合計 300 百萬元`, 72, 650, 1080, 24, 16, colors.body);
    slide.speakerNotes.textFrame.setText("示意資料：業務員 120、銀保 88、經代 54、直效 38 百萬元，合計 300。SVG 內嵌。" );
  }
  const candidate = path.join(build, "office-sample-candidate.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(candidate);
  const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href);
  await fs.rename(path.join(output, "transglobe-prototype.pptx"), path.join(build, "previous.pptx")).catch(error => { if (error.code !== "ENOENT") throw error; });
  await fs.rename(path.join(build, "pptx-validation.json"), path.join(build, "previous-validation.json")).catch(error => { if (error.code !== "ENOENT") throw error; });
  await finalizePresentation({
    explicitTotalSlideCount: 2,
    workspaceDir: root,
    candidatePath: candidate,
    finalPath: path.join(output, "transglobe-prototype.pptx"),
    pythonExecutable: python,
    integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
    fontPolicy: { basis: "user_request", families: ["Arial", "Microsoft JhengHei"] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(build, "pptx-validation.json"),
  });
}

async function createXlsx() {
  const workbook = Workbook.create();
  const visual = workbook.worksheets.add("Visual");
  const data = workbook.worksheets.add("Data");
  for (const sheet of [visual, data]) { sheet.showGridLines = false; sheet.tabColor = colors.focus; }
  data.getRange("A1:B1").values = [["通路", "保費（百萬元）"]];
  data.getRange("A2:B5").values = rows;
  data.getRange("A6:B6").values = [["合計", null]];
  data.getRange("B6").formulas = [["=SUM(B2:B5)"]];
  data.getRange("A1:B1").format = { fill: colors.focus, font: { name: "Microsoft JhengHei", color: "#FFFFFF", bold: true }, horizontalAlignment: "center" };
  data.getRange("A2:B6").format = { font: { name: "Microsoft JhengHei", color: colors.body }, borders: { preset: "all", style: "thin", color: "#D9D9D9" } };
  data.getRange("B2:B6").format.numberFormat = [["0"], ["0"], ["0"], ["0"], ["0"]];
  data.getRange("A6:B6").format.font = { name: "Microsoft JhengHei", bold: true, color: colors.body };
  data.getRange("A1:B6").format.columnWidth = 18;
  visual.getRange("A1:H1").merge();
  visual.getRange("A1").values = [[source.title_after ?? "通路保費組成"]];
  visual.getRange("A1").format = { font: { name: "Microsoft JhengHei", bold: true, color: colors.title, size: 20 } };
  visual.getRange("A2").values = [[period]];
  visual.getRange("A2").format.font = { name: "Microsoft JhengHei", color: colors.secondary, size: 11 };
  visual.getRange("A3").values = [["Before"]];
  visual.getRange("G3").values = [["After"]];
  visual.getRange("A3").format.font = { name: "Arial", bold: true, color: colors.compare };
  visual.getRange("G3").format.font = { name: "Arial", bold: true, color: colors.focus };
  visual.getRange("A20").values = [[`資料來源：${sourceNote}。資料見 Data 工作表。`]];
  visual.getRange("A20").format.font = { name: "Microsoft JhengHei", color: colors.secondary };
  visual.images.add({ svg: beforeSvg, alt: "Before 通路保費組成圖", anchor: { from: { row: 3, col: 0 }, extent: { widthPx: 480, heightPx: 210 } } });
  visual.images.add({ svg: afterSvg, alt: "After 通路保費組成圖", anchor: { from: { row: 3, col: 6 }, extent: { widthPx: 480, heightPx: 210 } } });
  workbook.recalculate();
  console.log((await workbook.inspect({kind: "table", range: "Data!A1:B6", include: "values,formulas", tableMaxRows: 6, tableMaxCols: 2})).ndjson);
  const workbookPath = path.join(output, "transglobe-prototype.xlsx");
  await (await SpreadsheetFile.exportXlsx(workbook)).save(workbookPath);
}

const part = process.env.OFFICE_PART ?? "all";
if (part === "all" || part === "pptx") await createPptx();
if (part === "all" || part === "xlsx") await createXlsx();
if (part === "all" || part === "docx") await run(python, [path.join(root, "create_docx.py"), path.join(root, "data.json"), path.join(assets, "chart-before.svg"), path.join(assets, "chart-after.svg"), path.join(output, "transglobe-prototype.docx")]);
