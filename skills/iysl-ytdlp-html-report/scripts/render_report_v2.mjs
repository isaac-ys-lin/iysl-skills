#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readAndValidateReport } from "./validate_report.mjs";

function usage() {
  console.error("用法：render_report_v2.mjs --spec <report-v2.json> [--markdown-out <report.md>] [--html-out <report.html> [--template <template.html>]]（至少指定一種輸出）");
  process.exit(2);
}

const args = process.argv.slice(2);
let specPath = "";
let markdownOut = "";
let htmlOut = "";
let templatePath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "assets", "report-v2-template.html");
let templateExplicit = false;
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--spec") specPath = args[++index] || usage();
  else if (args[index] === "--markdown-out") markdownOut = args[++index] || usage();
  else if (args[index] === "--html-out") htmlOut = args[++index] || usage();
  else if (args[index] === "--template") {
    templatePath = args[++index] || usage();
    templateExplicit = true;
  }
  else usage();
}
if (!specPath || (!markdownOut && !htmlOut) || (templateExplicit && !htmlOut)) usage();

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
const REPORT_SECTIONS = [
  { id: "recap", title: "內容重述", types: new Set(["narrative", "process", "comparison", "control-gap", "spotlight"]) },
  { id: "key-points", title: "洞見", types: new Set(["key-points"]) },
  { id: "food-for-thought", title: "food for thoughts", types: new Set(["food-for-thought"]) },
  { id: "actions", title: "可行啟發", types: new Set(["actions"]) },
];

function blockMarkdown(block) {
  const lines = [`### ${escapeMarkdown(block.title)}`];
  if (block.summary) lines.push("", escapeMarkdown(block.summary));
  if (block.type === "narrative") {
    block.paragraphs.forEach((item) => lines.push("", escapeMarkdown(item.text)));
  } else if (block.type === "process") {
    block.nodes.forEach((node, index) => lines.push("", `${index + 1}. **${escapeMarkdown(node.label)}**${node.detail ? ` — ${escapeMarkdown(node.detail)}` : ""}`));
  } else if (block.type === "comparison") {
    lines.push("", `| 比較面向 | ${block.columns.map(escapeMarkdownTable).join(" | ")} |`, `| --- | ${block.columns.map(() => "---").join(" | ")} |`);
    block.rows.forEach((row) => lines.push(`| ${escapeMarkdownTable(row.label)} | ${row.values.map(escapeMarkdownTable).join(" | ")} |`));
  } else if (block.type === "control-gap") {
    lines.push("", "| 控制點 | 逐字稿觀察 | 缺口 |", "| --- | --- | --- |");
    block.rows.forEach((row) => lines.push(`| ${escapeMarkdownTable(row.control)} | ${escapeMarkdownTable(row.observed)} | ${escapeMarkdownTable(row.gap)} |`));
  } else if (block.type === "spotlight") {
    block.items.forEach((item) => lines.push("", `#### ${escapeMarkdown(item.heading)}`, "", escapeMarkdown(item.text)));
  } else if (block.type === "actions") {
    block.items.forEach((item) => lines.push("", `- **${escapeMarkdown(item.action)}**${item.when ? ` — ${escapeMarkdown(item.when)}` : ""}`));
  } else if (block.type === "key-points") {
    block.items.forEach((item) => lines.push("", `#### ${escapeMarkdown(item.heading)}`, "", escapeMarkdown(item.text)));
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
  if (block.type === "narrative") {
    body += `<div class="narrative">${block.paragraphs.map((item) => `<p>${escapeHtml(item.text)}</p>`).join("")}</div>`;
  } else if (block.type === "process") {
    body += `<ol class="process">${block.nodes.map((node) => `<li><div><strong>${escapeHtml(node.label)}</strong>${node.detail ? `<p>${escapeHtml(node.detail)}</p>` : ""}</div></li>`).join("")}</ol>`;
  } else if (block.type === "comparison") {
    body += tableHtml(["比較面向", ...block.columns], block.rows.map((row) => [escapeHtml(row.label), ...row.values.map(escapeHtml)]));
  } else if (block.type === "control-gap") {
    body += tableHtml(["控制點", "逐字稿觀察", "缺口"], block.rows.map((row) => [escapeHtml(row.control), escapeHtml(row.observed), escapeHtml(row.gap)]));
  } else if (block.type === "spotlight") {
    body += `<div class="spotlight" data-spotlight-angle="${escapeHtml(block.angle)}">${block.items.map((item) => `<article><h4>${escapeHtml(item.heading)}</h4><p>${escapeHtml(item.text)}</p></article>`).join("")}</div>`;
  } else if (block.type === "actions") {
    body += `<ul class="actions">${block.items.map((item) => `<li><strong>${escapeHtml(item.action)}</strong>${item.when ? `<p class="when">${escapeHtml(item.when)}</p>` : ""}</li>`).join("")}</ul>`;
  } else if (block.type === "key-points") {
    body += `<div class="key-points">${block.items.map((item) => `<article><h4>${escapeHtml(item.heading)}</h4><p>${escapeHtml(item.text)}</p></article>`).join("")}</div>`;
  } else if (block.type === "food-for-thought") {
    body += `<div class="thoughts">${block.items.map((item) => `<article><h4>${escapeHtml(item.prompt)}</h4>${item.context ? `<p>${escapeHtml(item.context)}</p>` : ""}</article>`).join("")}</div>`;
  }
  return `<article id="${escapeHtml(block.id)}" class="report-block block-${escapeHtml(block.type)}" data-report-block="${escapeHtml(block.id)}" data-report-block-type="${escapeHtml(block.type)}"><header><h3>${escapeHtml(block.title)}</h3></header>${body}</article>`;
}

const spec = readAndValidateReport(specPath);
const result = { valid: true, blocks: spec.blocks.length };

if (markdownOut) {
  const markdownSections = REPORT_SECTIONS.map((section) => {
    const blocks = spec.blocks.filter((block) => section.types.has(block.type));
    return `## ${section.title}\n\n${blocks.map(blockMarkdown).join("\n\n")}`;
  }).join("\n\n");
  const briefMarkdown = [
    escapeMarkdown(spec.brief.claim.text),
    "",
    ...spec.brief.takeaways.map((takeaway) => `- **${escapeMarkdown(takeaway.text)}**`),
    ...(spec.source_limitation ? [
      "",
      `> ${escapeMarkdown(spec.source_limitation.notice)} [回到原影片](${spec.source.url})`,
    ] : []),
  ].join("\n");
  const markdown = [
    `# ${escapeMarkdown(spec.title)}`,
    spec.subtitle ? `\n${escapeMarkdown(spec.subtitle)}` : "",
    "",
    `來源：${spec.source.url}`,
    "",
    briefMarkdown,
    "",
    markdownSections,
    "",
  ].join("\n");
  writeFileSync(markdownOut, markdown, "utf8");
  result.markdown = markdownOut;
}

if (htmlOut) {
  let template = readFileSync(templatePath, "utf8");
  const replacements = {
    title: escapeHtml(spec.title),
    subtitleHtml: spec.subtitle ? `<p class="subtitle">${escapeHtml(spec.subtitle)}</p>` : "",
    sourceUrl: escapeHtml(spec.source.url),
    channel: escapeHtml(spec.source.channel || ""),
    duration: escapeHtml(spec.source.duration || ""),
    readingMinutes: `閱讀約 ${escapeHtml(String(spec.reading_minutes))} 分鐘`,
    thumbnailHtml: spec.source.thumbnail_url
      ? `<a class="media-anchor" href="${escapeHtml(spec.source.url)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(spec.source.thumbnail_url)}" alt="${escapeHtml(spec.title)} 的影片縮圖"></a>`
      : "",
    briefHtml: [
      '<section class="report-brief" data-report-brief>',
      `<p class="brief-claim">${escapeHtml(spec.brief.claim.text)}</p>`,
      "<ol class=\"brief-takeaways\">",
      ...spec.brief.takeaways.map((takeaway) => `<li>${escapeHtml(takeaway.text)}</li>`),
      "</ol>",
      ...(spec.source_limitation ? [
        `<p class="source-limitation">${escapeHtml(spec.source_limitation.notice)} <a href="${escapeHtml(spec.source.url)}" target="_blank" rel="noreferrer">回到原影片</a></p>`,
      ] : []),
      "</section>",
    ].join(""),
    sectionsHtml: REPORT_SECTIONS.map((section) => {
      const blocks = spec.blocks.filter((block) => section.types.has(block.type));
      return `<section id="section-${section.id}" class="report-section" data-report-section="${section.id}"><header><h2>${section.title}</h2></header>${blocks.map(blockHtml).join("\n")}</section>`;
    }).join("\n"),
  };
  for (const [key, value] of Object.entries(replacements)) template = template.replaceAll(`{{${key}}}`, value);
  if (/\{\{[^}]+\}\}/.test(template)) throw new Error("v2 template 含未替換 placeholder");
  writeFileSync(htmlOut, template, "utf8");
  result.html = htmlOut;
}

console.log(JSON.stringify(result, null, 2));
