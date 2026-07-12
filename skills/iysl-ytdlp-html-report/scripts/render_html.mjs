#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);

function usage() {
  console.error("用法：render_html.mjs --report <報告.md> --metadata <metadata.json> --out <報告.html> [--template <template.html>]");
  process.exit(2);
}

let reportPath = "";
let metadataPath = "";
let outPath = "";
let templatePath = path.join(path.dirname(new URL(import.meta.url).pathname), "..", "assets", "report-template.html");

for (let i = 0; i < args.length; i += 1) {
  if (args[i] === "--report") reportPath = args[++i] || usage();
  else if (args[i] === "--metadata") metadataPath = args[++i] || usage();
  else if (args[i] === "--out") outPath = args[++i] || usage();
  else if (args[i] === "--template") templatePath = args[++i] || usage();
  else usage();
}

if (!reportPath || !metadataPath || !outPath) usage();

const report = readFileSync(reportPath, "utf8");
const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
let template = readFileSync(templatePath, "utf8");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function splitTitle(value) {
  const title = String(value || "影片報告").trim();
  const separators = ["｜", " | ", " - ", " – ", " — "];
  for (const separator of separators) {
    const index = title.indexOf(separator);
    if (index <= 0) continue;
    const main = title.slice(0, index).trim();
    const sub = title.slice(index + separator.length).trim();
    if (main.length >= 6 && sub.length >= 4) return { main, sub };
  }
  return { main: title, sub: "" };
}

function normalizeHeading(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[：:]/g, "")
    .replace(/\s+/g, " ");
}

function sectionKey(heading) {
  const h = normalizeHeading(heading);
  if (h === "food for thoughts" || h === "food for thought") return "food";
  if (h === "洞見" || h === "洞见") return "insights";
  if (h === "重述" || h === "內容重述" || h === "摘要" || h === "summary") return "summary";
  if (h === "可行啟發" || h === "可行启发" || h === "actions") return "actions";
  if (h === "驗證與限制" || h === "验证与限制" || h === "verification") return "verification";
  return "";
}

function splitSections(markdown) {
  const sections = { food: "", insights: "", summary: "", actions: "", verification: "" };
  let current = "";
  for (const line of markdown.split(/\r?\n/)) {
    const match = line.match(/^#{1,3}\s+(.+?)\s*$/);
    if (match) {
      const key = sectionKey(match[1]);
      current = key || current;
      if (key) continue;
    }
    if (current && Object.hasOwn(sections, current)) {
      sections[current] += `${line}\n`;
    }
  }
  return sections;
}

function inlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function markdownToHtml(markdown) {
  const lines = markdown.trim().split(/\r?\n/);
  const html = [];
  let paragraph = [];
  let list = null;

  function flushParagraph() {
    if (paragraph.length) {
      html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  }

  function closeList() {
    if (list) {
      html.push(`</${list}>`);
      list = null;
    }
  }

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      closeList();
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.+)$/);
    const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (bullet || ordered) {
      flushParagraph();
      const type = ordered ? "ol" : "ul";
      if (list !== type) {
        closeList();
        list = type;
        html.push(`<${type}>`);
      }
      html.push(`<li>${inlineMarkdown((bullet || ordered)[1])}</li>`);
      continue;
    }
    const heading = line.match(/^#{1,4}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      closeList();
      html.push(`<h3>${inlineMarkdown(heading[1])}</h3>`);
      continue;
    }
    paragraph.push(line);
  }
  flushParagraph();
  closeList();
  return html.join("\n");
}

const sections = splitSections(report);
const missing = Object.entries(sections).filter(([, value]) => !value.trim()).map(([key]) => key);
if (missing.length) {
  throw new Error(`報告缺少必要區塊：${missing.join(", ")}`);
}

const titleParts = splitTitle(metadata.title);
const replacements = {
  title: metadata.title || "影片報告",
  heroMain: titleParts.main,
  heroSubHtml: titleParts.sub ? `<p class="title-sub">${escapeHtml(titleParts.sub)}</p>` : "",
  channel: metadata.channel || metadata.uploader || "",
  sourceUrl: metadata.webpage_url || metadata.original_url || "",
  originalUrl: metadata.original_url || "",
  duration: metadata.duration_string || "",
  thumbnail: metadata.thumbnail || "",
  extractedAt: metadata.extracted_at || "",
  foodHtml: markdownToHtml(sections.food),
  insightsHtml: markdownToHtml(sections.insights),
  summaryHtml: markdownToHtml(sections.summary),
  actionsHtml: markdownToHtml(sections.actions),
  verificationHtml: markdownToHtml(sections.verification),
};

for (const [key, value] of Object.entries(replacements)) {
  const htmlValue = key.endsWith("Html") ? value : escapeHtml(value);
  template = template.replaceAll(`{{${key}}}`, htmlValue);
}

writeFileSync(outPath, template);
console.log(JSON.stringify({ out: outPath, sections: Object.keys(sections), source: metadata.webpage_url }, null, 2));
