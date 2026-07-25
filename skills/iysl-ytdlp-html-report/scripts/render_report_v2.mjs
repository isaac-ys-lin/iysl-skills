#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readAndValidateReportV2 } from "./validate_report_v2.mjs";

function usage() {
  console.error("用法：render_report_v2.mjs --spec <report-v2.json> --markdown-out <report.md> --html-out <report.html> [--template <template.html>]");
  process.exit(2);
}

const args = process.argv.slice(2);
let specPath = "";
let markdownOut = "";
let htmlOut = "";
let templatePath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "assets", "report-v2-template.html");
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--spec") specPath = args[++index] || usage();
  else if (args[index] === "--markdown-out") markdownOut = args[++index] || usage();
  else if (args[index] === "--html-out") htmlOut = args[++index] || usage();
  else if (args[index] === "--template") templatePath = args[++index] || usage();
  else usage();
}
if (!specPath || !markdownOut || !htmlOut) usage();

const escapeHtml = (value) => String(value ?? "")
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");

const escapeMarkdown = (value) => String(value ?? "")
  .replace(/\r?\n/g, " ")
  .replace(/\\/g, "\\\\")
  .replace(/([`*_[\]<>])/g, "\\$1");
const escapeMarkdownTable = (value) => escapeMarkdown(value).replace(/\|/g, "\\|");
const transcriptKindLabel = {
  native_captions: "原生字幕",
  auto_captions: "自動字幕",
  audio_asr: "音訊 ASR",
};

function blockMarkdown(block) {
  const lines = [`## ${escapeMarkdown(block.title)}`];
  if (block.summary) lines.push("", escapeMarkdown(block.summary));
  if (block.type === "process") {
    block.nodes.forEach((node, index) => lines.push("", `${index + 1}. **${escapeMarkdown(node.label)}**${node.detail ? ` — ${escapeMarkdown(node.detail)}` : ""}`));
  } else if (block.type === "comparison") {
    lines.push("", `| 比較面向 | ${block.columns.map(escapeMarkdownTable).join(" | ")} |`, `| --- | ${block.columns.map(() => "---").join(" | ")} |`);
    block.rows.forEach((row) => lines.push(`| ${escapeMarkdownTable(row.label)} | ${row.values.map(escapeMarkdownTable).join(" | ")} |`));
  } else if (block.type === "control-gap") {
    lines.push("", "| 控制點 | 逐字稿觀察 | 缺口 |", "| --- | --- | --- |");
    block.rows.forEach((row) => lines.push(`| ${escapeMarkdownTable(row.control)} | ${escapeMarkdownTable(row.observed)} | ${escapeMarkdownTable(row.gap)} |`));
  } else if (block.type === "actions") {
    block.items.forEach((item) => lines.push("", `- **${escapeMarkdown(item.action)}**${item.when ? ` — ${escapeMarkdown(item.when)}` : ""}`));
  } else if (block.type === "key-points") {
    block.items.forEach((item) => lines.push("", `### ${escapeMarkdown(item.heading)}`, "", escapeMarkdown(item.text)));
  } else if (block.type === "food-for-thought") {
    block.items.forEach((item) => lines.push("", `> **${escapeMarkdown(item.prompt)}**${item.context ? `\n>\n> ${escapeMarkdown(item.context)}` : ""}`));
  }
  return lines.join("\n");
}

function tableHtml(headers, rows) {
  return `<div class="table-wrap"><table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function blockHtml(block) {
  let body = "";
  if (block.summary) body += `<p class="summary">${escapeHtml(block.summary)}</p>`;
  if (block.type === "process") {
    body += `<ol class="process">${block.nodes.map((node) => `<li><div><strong>${escapeHtml(node.label)}</strong>${node.detail ? `<p>${escapeHtml(node.detail)}</p>` : ""}</div></li>`).join("")}</ol>`;
  } else if (block.type === "comparison") {
    body += tableHtml(["比較面向", ...block.columns], block.rows.map((row) => [escapeHtml(row.label), ...row.values.map(escapeHtml)]));
  } else if (block.type === "control-gap") {
    body += tableHtml(["控制點", "逐字稿觀察", "缺口"], block.rows.map((row) => [escapeHtml(row.control), escapeHtml(row.observed), escapeHtml(row.gap)]));
  } else if (block.type === "actions") {
    body += `<ul class="actions">${block.items.map((item) => `<li><strong>${escapeHtml(item.action)}</strong>${item.when ? `<p>${escapeHtml(item.when)}</p>` : ""}</li>`).join("")}</ul>`;
  } else if (block.type === "key-points") {
    body += `<div class="key-points">${block.items.map((item) => `<article><h3>${escapeHtml(item.heading)}</h3><p>${escapeHtml(item.text)}</p></article>`).join("")}</div>`;
  } else if (block.type === "food-for-thought") {
    body += `<div class="thoughts">${block.items.map((item) => `<article><span aria-hidden="true">?</span><div><h3>${escapeHtml(item.prompt)}</h3>${item.context ? `<p>${escapeHtml(item.context)}</p>` : ""}</div></article>`).join("")}</div>`;
  }
  return `<section id="${escapeHtml(block.id)}" class="report-block block-${escapeHtml(block.type)}"><header><h2>${escapeHtml(block.title)}</h2></header>${body}</section>`;
}

const spec = readAndValidateReportV2(specPath);
const markdownBlocks = spec.blocks.map(blockMarkdown).join("\n\n");
const footerNote = `${transcriptKindLabel[spec.source.transcript_kind]} 整理；未下載或檢視影片畫面。`;
const markdown = [
  `# ${escapeMarkdown(spec.title)}`,
  spec.subtitle ? `\n${escapeMarkdown(spec.subtitle)}` : "",
  "",
  `來源：${spec.source.url}`,
  "",
  markdownBlocks,
  "",
  "---",
  "",
  `*${escapeMarkdown(footerNote)}*`,
  "",
].join("\n");

let template = readFileSync(templatePath, "utf8");
const replacements = {
  title: escapeHtml(spec.title),
  subtitleHtml: spec.subtitle ? `<p class="subtitle">${escapeHtml(spec.subtitle)}</p>` : "",
  sourceUrl: escapeHtml(spec.source.url),
  channel: escapeHtml(spec.source.channel || ""),
  duration: escapeHtml(spec.source.duration || ""),
  thumbnailHtml: spec.source.thumbnail_url
    ? `<a class="media-anchor" href="${escapeHtml(spec.source.url)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(spec.source.thumbnail_url)}" alt="${escapeHtml(spec.title)} 的影片縮圖"></a>`
    : "",
  blocksHtml: spec.blocks.map(blockHtml).join("\n"),
  footerNote: escapeHtml(footerNote),
};
for (const [key, value] of Object.entries(replacements)) template = template.replaceAll(`{{${key}}}`, value);
if (/\{\{[^}]+\}\}/.test(template)) throw new Error("v2 template 含未替換 placeholder");

writeFileSync(markdownOut, markdown, "utf8");
writeFileSync(htmlOut, template, "utf8");
console.log(JSON.stringify({ valid: true, markdown: markdownOut, html: htmlOut, blocks: spec.blocks.length }, null, 2));
