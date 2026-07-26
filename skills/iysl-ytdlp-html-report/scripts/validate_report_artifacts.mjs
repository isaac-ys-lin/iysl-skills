#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { readAndValidateReportV2 } from "./validate_report_v2.mjs";

const SECTION_TITLES = ["內容重述", "洞見", "food for thoughts", "可行啟發"];
const SIDECAR_FIELDS = [
  "source_url",
  "resolved_url",
  "video_id",
  "metadata_path",
  "transcript_path",
  "report_markdown_path",
  "report_html_path",
  "presentation_backend",
  "presentation_fallback_reason",
  "subtitle_source",
  "extraction_tool",
  "transcription_method",
  "asr_backend",
  "asr_model",
  "asr_network_policy",
  "transcript_normalization",
  "audio_preprocess",
  "audio_cache_path",
  "extracted_at",
];
const COMMAND_FIELDS = [
  "transcript_extract",
  "html_render",
  "html_parse",
  "section_scan",
  "deterministic_verification",
];
const FORBIDDEN_READER_TEXT = [
  "驗證與限制",
  "claim_type",
  "evidence_refs",
  "Command Evidence",
  "metadata_path",
  "transcript_path",
  "presentation_backend",
  "presentation_fallback_reason",
];
const FORBIDDEN_READER_PATTERNS = [
  /本報告使用(?:原生|自動)?字幕/,
  /逐字稿來自(?:字幕|音訊|自動轉錄)/,
  /(?:無|沒有)原生字幕/,
  /未(?:下載|檢視|觀看)(?:影片|影片畫面|畫面)/,
  /(?:專名|人名|數字).{0,12}可能誤聽/,
  /(?:字幕|轉錄|逐字稿)(?:來源|品質|限制)/,
  /(?:字幕.{0,12}(?:自動生成|自動產生|自動轉錄|機器生成|機器產生)|(?:自動生成|自動產生|自動轉錄|機器生成|機器產生).{0,12}字幕)/,
  /(?:(?:畫面|視覺).{0,12}(?:未經|沒有|尚未|未).{0,8}(?:人工)?(?:核對|確認|檢查|檢視|觀看)|(?:未經|沒有|尚未|未).{0,8}(?:人工)?(?:核對|確認|檢查|檢視|觀看).{0,12}(?:畫面|視覺))/,
];

function usage() {
  console.error("用法：validate_report_artifacts.mjs --spec <report-v2.json> --markdown <report.md> --html <report.html> --sidecar <verification.md>");
  process.exit(2);
}

function decodeEntities(value) {
  const named = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
  return value.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (match, entity) => {
    if (entity[0] === "#") {
      const radix = entity[1].toLowerCase() === "x" ? 16 : 10;
      const digits = radix === 16 ? entity.slice(2) : entity.slice(1);
      const codePoint = Number.parseInt(digits, radix);
      return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : match;
    }
    return named[entity.toLowerCase()] ?? match;
  });
}

function normalize(value) {
  return decodeEntities(String(value))
    .replace(/\\([\\`*_[\]<>|])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function htmlToText(html) {
  return normalize(
    html
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " "),
  );
}

function containsLocalPath(value) {
  const withoutWebUrls = value.replace(/https?:\/\/\S+/gi, " ");
  return /(?:file:\/\/|(?:^|[^A-Za-z0-9._/-])\/(?!\/)\S+|(?:^|[^A-Za-z0-9._/-])[A-Za-z]:[\\/]\S*)/i.test(withoutWebUrls);
}

function sidecarSectionHasEntry(sidecar, heading) {
  const headingMatch = new RegExp(`^##\\s+${heading}\\s*$`, "m").exec(sidecar);
  if (!headingMatch) return false;
  const bodyStart = headingMatch.index + headingMatch[0].length;
  const remainder = sidecar.slice(bodyStart);
  const nextHeading = /^##\s+/m.exec(remainder);
  const body = nextHeading ? remainder.slice(0, nextHeading.index) : remainder;
  return /^-\s+\S.*$/m.test(body);
}

function blockAnchors(block) {
  const anchors = [block.title, block.summary];
  if (block.type === "narrative") block.paragraphs.forEach((item) => anchors.push(item.text));
  else if (block.type === "process") block.nodes.forEach((item) => anchors.push(item.label, item.detail));
  else if (block.type === "comparison") {
    anchors.push(...block.columns);
    block.rows.forEach((item) => anchors.push(item.label, ...item.values));
  } else if (block.type === "control-gap") {
    block.rows.forEach((item) => anchors.push(item.control, item.observed, item.gap));
  } else if (block.type === "actions") block.items.forEach((item) => anchors.push(item.action, item.when));
  else if (block.type === "key-points") block.items.forEach((item) => anchors.push(item.heading, item.text));
  else if (block.type === "food-for-thought") block.items.forEach((item) => anchors.push(item.prompt, item.context));
  return anchors.filter((value) => typeof value === "string" && value.trim());
}

const args = process.argv.slice(2);
const paths = {};
for (let index = 0; index < args.length; index += 2) {
  const key = args[index];
  const value = args[index + 1];
  if (!["--spec", "--markdown", "--html", "--sidecar"].includes(key) || !value) usage();
  paths[key.slice(2)] = value;
}
if (Object.keys(paths).length !== 4) usage();

try {
  const spec = readAndValidateReportV2(paths.spec);
  const markdown = readFileSync(paths.markdown, "utf8");
  const html = readFileSync(paths.html, "utf8");
  const sidecar = readFileSync(paths.sidecar, "utf8");
  const errors = [];
  const markdownText = normalize(markdown);
  const htmlText = htmlToText(html);

  const markdownSections = [...markdown.matchAll(/^##\s+(.+?)\s*$/gm)].map((match) => normalize(match[1]));
  const htmlSections = [...html.matchAll(/<h2\b[^>]*>([\s\S]*?)<\/h2>/gi)].map((match) => htmlToText(match[1]));
  if (JSON.stringify(markdownSections) !== JSON.stringify(SECTION_TITLES)) {
    errors.push(`Markdown 四章不完整或順序錯誤：${markdownSections.join(" → ")}`);
  }
  if (JSON.stringify(htmlSections) !== JSON.stringify(SECTION_TITLES)) {
    errors.push(`HTML 四章不完整或順序錯誤：${htmlSections.join(" → ")}`);
  }

  for (const anchor of spec.blocks.flatMap(blockAnchors).map(normalize)) {
    if (!markdownText.includes(anchor)) errors.push(`Markdown 遺漏 spec 內容：${anchor}`);
    if (!htmlText.includes(anchor)) errors.push(`HTML 遺漏 spec 內容：${anchor}`);
  }
  for (const [label, output, readerText] of [["Markdown", markdown, markdownText], ["HTML", html, htmlText]]) {
    for (const forbidden of FORBIDDEN_READER_TEXT) {
      if (output.includes(forbidden)) errors.push(`${label} 含 reader-facing 禁止文字：${forbidden}`);
    }
    for (const pattern of FORBIDDEN_READER_PATTERNS) {
      if (pattern.test(readerText)) errors.push(`${label} 含 reader-facing 來源或轉錄限制：${pattern.source}`);
    }
    if (containsLocalPath(readerText)) errors.push(`${label} 含絕對本機路徑`);
  }
  if (/<script\b/i.test(html)) errors.push("HTML 不可包含 script");
  for (const field of SIDECAR_FIELDS) {
    if (!new RegExp(`^-[ \\t]*${field}:[ \\t]*[^\\r\\n]*\\S[^\\r\\n]*$`, "m").test(sidecar)) {
      errors.push(`sidecar 缺少非空欄位：${field}`);
    }
  }
  for (const field of COMMAND_FIELDS) {
    if (!new RegExp(`^-[ \\t]*${field}:[ \\t]*[^\\r\\n]*\\S[^\\r\\n]*$`, "m").test(sidecar)) {
      errors.push(`sidecar Command Evidence 缺少非空欄位：${field}`);
    }
  }
  if (!COMMAND_FIELDS.some((field) => new RegExp(`^-[ \\t]*${field}:[ \\t]*[^\\r\\n]*\\S[^\\r\\n]*$`, "m").test(sidecar))) {
    errors.push("sidecar 缺少非空 Command Evidence");
  }
  if (!sidecarSectionHasEntry(sidecar, "Limits")) errors.push("sidecar 缺少非空 Limits");

  if (errors.length) throw new Error(`report artifact 驗證失敗：\n- ${errors.join("\n- ")}`);
  console.log(JSON.stringify({ valid: true, sections: SECTION_TITLES, blocks: spec.blocks.length }, null, 2));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
