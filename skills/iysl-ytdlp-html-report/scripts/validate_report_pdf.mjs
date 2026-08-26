#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";

const REQUIRED_SECTIONS = ["內容重述", "洞見", "foodforthoughts", "可行啟發"];

function usage(exitCode = 2) {
  console.error("用法：validate_report_pdf.mjs --pdf <report.pdf> [--qa-dir <empty-directory>]");
  process.exit(exitCode);
}

function parseArgs(args) {
  const options = { pdf: "", qaDir: "" };
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    const value = args[index + 1];
    if (!["--pdf", "--qa-dir"].includes(key) || !value || value.startsWith("--")) usage();
    if (key === "--pdf") options.pdf = value;
    else options.qaDir = value;
    index += 1;
  }
  if (!options.pdf) usage();
  return options;
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (result.error?.code === "ENOENT") throw new Error(`PDF QA 需要 ${command}；請安裝 Poppler`);
  if (result.status !== 0) {
    const detail = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
    throw new Error(`${command} 失敗（exit ${result.status}）：${detail || "no output"}`);
  }
  return result.stdout;
}

function field(info, name) {
  return new RegExp(`^${name}:\\s*(.+)$`, "mi").exec(info)?.[1]?.trim() || "";
}

function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  const pdfPath = path.resolve(options.pdf);
  if (!existsSync(pdfPath) || !readFileSync(pdfPath).subarray(0, 5).equals(Buffer.from("%PDF-"))) {
    throw new Error(`不是有效 PDF：${pdfPath}`);
  }
  const info = run("pdfinfo", [pdfPath]);
  const pages = Number.parseInt(field(info, "Pages"), 10);
  if (!Number.isInteger(pages) || pages < 1) throw new Error("PDF pages 必須至少為 1");
  if (field(info, "Encrypted").toLowerCase() !== "no") throw new Error("PDF 不可加密");
  if ((field(info, "JavaScript") || "no").toLowerCase() !== "no") throw new Error("PDF 不可包含 JavaScript");
  const size = /([0-9.]+)\s+x\s+([0-9.]+)\s+pts/i.exec(field(info, "Page size"));
  if (!size || Math.abs(Number(size[1]) - 595) > 3 || Math.abs(Number(size[2]) - 842) > 3) {
    throw new Error(`PDF page size 必須是 A4；實際為 ${field(info, "Page size") || "unknown"}`);
  }
  const text = run("pdftotext", [pdfPath, "-"]);
  if (/file:\s*\/\//i.test(text)) throw new Error("PDF 文字層洩漏 file URL；頁首頁尾必須關閉");
  const normalizedText = text.replace(/\s+/g, "").toLowerCase();
  if (normalizedText.length < 200) throw new Error("PDF 缺少可用文字層或內容過少");
  for (const section of REQUIRED_SECTIONS) {
    if (!normalizedText.includes(section.toLowerCase())) throw new Error(`PDF 文字層遺漏章節：${section}`);
  }

  let pageImages = [];
  if (options.qaDir) {
    const qaDir = path.resolve(options.qaDir);
    if (existsSync(qaDir) && readdirSync(qaDir).length) throw new Error(`--qa-dir 必須不存在或為空：${qaDir}`);
    mkdirSync(qaDir, { recursive: true });
    run("pdftoppm", ["-png", "-r", "96", pdfPath, path.join(qaDir, "page")]);
    pageImages = readdirSync(qaDir)
      .filter((name) => /^page-\d+\.png$/i.test(name))
      .sort()
      .map((name) => path.join(qaDir, name));
    if (pageImages.length !== pages) {
      throw new Error(`PDF QA 頁圖數量不符：pages=${pages}, images=${pageImages.length}`);
    }
  }

  console.log(JSON.stringify({
    valid: true,
    report_pdf: pdfPath,
    pages,
    page_size: "A4",
    text_layer: "verified",
    required_sections: "verified",
    page_images: pageImages,
    visual_review_required: true,
  }, null, 2));
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
