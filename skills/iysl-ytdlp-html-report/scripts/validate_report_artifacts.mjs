#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { readAndValidateReportV2 } from "./validate_report_v2.mjs";

const SECTION_TITLES = ["內容重述", "洞見", "food for thoughts", "可行啟發"];
// 章節識別的權威是結構化錨點，不是標題文字或標題層級：排版可以自由決定
// 標題怎麼下，語意骨架仍然可驗。
const SECTION_ANCHORS = ["recap", "key-points", "food-for-thought", "actions"];
// 「排版器不能加事實」在這裡是結構檢查，不是語意檢查：每一個 sectioning 元素
// 都必須指回 spec 的章節，或明確宣告自己是沒有證據來源的 chrome。它擋得住整段
// 憑空生出來的內容，擋不住在已宣告區塊內改寫語氣。
const SECTIONING_ELEMENTS = ["section", "article", "nav", "aside", "header", "footer"];
const CHROME_KINDS = ["cover", "toc", "running-head"];
// block type 歸到哪一章，是語意契約而不是排版偏好。外部排版器把 actions 的內容
// 擺進 recap 也能通過「文字有出現」的檢查，但 Markdown 版會照真正的對應渲染，
// 兩份交付物就會講不同的故事。
const BLOCK_SECTION = new Map([
  ["narrative", "recap"], ["process", "recap"], ["comparison", "recap"], ["control-gap", "recap"],
  ["key-points", "key-points"],
  ["food-for-thought", "food-for-thought"],
  ["actions", "actions"],
]);
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

const VOID_ELEMENTS = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]);
const OPAQUE_ELEMENTS = new Set(["script", "style", "template", "head"]);
const TAG = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[^\s=/>]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*))?)*)\s*(\/?)>/g;

// 屬性要真的解析出來。用正規表示式在整段原始文字裡找 data-report-*，會讓錨點
// 藏在註解裡也算數，也會讓宣告被偽造在別的屬性值裡（例如 title="...")。
function parseAttributes(raw) {
  const attributes = new Map();
  const pattern = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]*)))?/g;
  for (const match of String(raw || "").matchAll(pattern)) {
    const name = match[1].toLowerCase();
    if (!name) continue;
    attributes.set(name, match[2] ?? match[3] ?? match[4] ?? "");
  }
  return attributes;
}

function describeElement(tag, attributes, excerpt) {
  const id = attributes.get("id");
  const className = attributes.get("class");
  if (id) return `<${tag} id="${id}">`;
  if (className) return `<${tag} class="${className}">`;
  const text = (excerpt || "").replace(/\s+/g, " ").trim().slice(0, 24);
  return text ? `<${tag}>（開頭是「${text}」）` : `<${tag}>`;
}

// 走訪 body，回報三件事：宣告過的章節錨點順序、brief 的位置，以及任何沒有被
// 任何宣告涵蓋的讀者內容。宣告可以掛在任何元素上，不限 sectioning 元素。
function auditDocument(html) {
  const problems = [];
  const anchors = [];
  const withoutComments = html.replace(/<!--[\s\S]*?-->/g, "");
  const bodyMatch = /<body\b[^>]*>([\s\S]*)<\/body>/i.exec(withoutComments);
  const body = bodyMatch ? bodyMatch[1] : withoutComments;

  const stack = [];
  const sectionText = new Map();
  let briefCount = 0;
  let briefBeforeSections = true;
  let opaque = null;
  let cursor = 0;
  TAG.lastIndex = 0;
  for (const match of body.matchAll(TAG)) {
    const between = body.slice(cursor, match.index);
    cursor = match.index + match[0].length;
    const closing = match[1] === "/";
    const tag = match[2].toLowerCase();
    const attributes = parseAttributes(match[3]);
    const selfClosing = match[4] === "/" || VOID_ELEMENTS.has(tag);

    if (!opaque && between.trim()) {
      for (const entry of stack) {
        if (entry.anchor) sectionText.set(entry.anchor, (sectionText.get(entry.anchor) || "") + between);
      }
    }
    if (!opaque && between.trim() && !stack.some((entry) => entry.declared)) {
      problems.push(`未經宣告的讀者內容：「${between.replace(/\s+/g, " ").trim().slice(0, 24)}」`);
    }
    if (opaque) {
      if (closing && tag === opaque) opaque = null;
      continue;
    }
    if (!closing && OPAQUE_ELEMENTS.has(tag)) {
      if (!selfClosing) opaque = tag;
      continue;
    }
    if (closing) {
      for (let index = stack.length - 1; index >= 0; index -= 1) {
        if (stack[index].tag === tag) {
          stack.splice(index, 1);
          break;
        }
      }
      continue;
    }

    const covered = stack.some((entry) => entry.declared);
    const section = attributes.get("data-report-section");
    const chrome = attributes.get("data-report-chrome");
    const brief = attributes.has("data-report-brief");
    const declarations = [section !== undefined, chrome !== undefined, brief].filter(Boolean).length;
    let declared = false;

    if (declarations > 1) {
      problems.push(`${describeElement(tag, attributes)} 同時宣告了一個以上的 data-report-* 錨點`);
      declared = true;
    } else if (declarations === 1 && covered) {
      // 已宣告區塊內的巢狀宣告不重複計數，但仍視為已涵蓋。
      declared = true;
      if (section !== undefined && !SECTION_ANCHORS.includes(section.trim())) {
        problems.push(`${describeElement(tag, attributes)} 的章節錨點未定義：${section.trim()}`);
      }
    } else if (declarations === 1) {
      declared = true;
      if (section !== undefined) {
        if (!SECTION_ANCHORS.includes(section.trim())) {
          problems.push(`${describeElement(tag, attributes)} 的章節錨點未定義：${section.trim()}`);
        }
        anchors.push(section.trim());
      } else if (chrome !== undefined) {
        if (!CHROME_KINDS.includes(chrome.trim())) {
          problems.push(`${describeElement(tag, attributes)} 的 chrome 宣告未定義：${chrome.trim()}`);
        }
      } else {
        briefCount += 1;
        if (anchors.length) briefBeforeSections = false;
      }
    } else if (!covered && SECTIONING_ELEMENTS.includes(tag)) {
      problems.push(`${describeElement(tag, attributes, body.slice(cursor, cursor + 60))} 沒有 spec 錨點也沒有 chrome 宣告`);
    }

    if (!selfClosing) {
      const anchor = declarations === 1 && section !== undefined && !covered ? section.trim() : null;
      stack.push({ tag, declared, anchor: anchor || stack.find((entry) => entry.anchor)?.anchor || null });
    }
  }

  const tail = body.slice(cursor);
  if (tail.trim()) {
    problems.push(`未經宣告的讀者內容：「${tail.replace(/\s+/g, " ").trim().slice(0, 24)}」`);
  }
  return { problems, anchors, briefCount, briefBeforeSections, sectionText };
}

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
  const audit = auditDocument(html);
  for (const problem of audit.problems) {
    errors.push(`HTML ${problem}`);
  }
  const htmlAnchors = audit.anchors;
  if (JSON.stringify(markdownSections) !== JSON.stringify(SECTION_TITLES)) {
    errors.push(`Markdown 四章不完整或順序錯誤：${markdownSections.join(" → ")}`);
  }
  if (audit.briefCount === 0) {
    errors.push("HTML 缺少 brief 掃讀層");
  } else if (audit.briefCount > 1) {
    errors.push(`HTML 的 brief 出現 ${audit.briefCount} 次，必須恰好一個`);
  } else if (!audit.briefBeforeSections) {
    errors.push("HTML 的 brief 必須位於四章之前");
  }
  const briefAnchors = [spec.brief.claim.text, ...spec.brief.takeaways.map((item) => item.text)].map(normalize);
  for (const anchor of briefAnchors) {
    if (!markdownText.includes(anchor)) errors.push(`Markdown 遺漏 brief 內容：${anchor}`);
    if (!htmlText.includes(anchor)) errors.push(`HTML 遺漏 brief 內容：${anchor}`);
  }
  const htmlIds = [...html.matchAll(/\sid\s*=\s*"([^"]*)"/gi)].map((match) => match[1].trim());
  const duplicateIds = [...new Set(htmlIds.filter((id, index) => id && htmlIds.indexOf(id) !== index))];
  if (duplicateIds.length) {
    errors.push(`HTML 有重複的 id：${duplicateIds.join("、")}`);
  }
  const missingAnchors = SECTION_ANCHORS.filter((anchor) => !htmlAnchors.includes(anchor));
  const unknownAnchors = htmlAnchors.filter((anchor) => !SECTION_ANCHORS.includes(anchor));
  const duplicateAnchors = SECTION_ANCHORS.filter((anchor) => htmlAnchors.filter((seen) => seen === anchor).length > 1);
  if (missingAnchors.length) {
    errors.push(`HTML 缺少章節錨點：${missingAnchors.join("、")}`);
  }
  if (unknownAnchors.length) {
    errors.push(`HTML 含未定義的章節錨點：${unknownAnchors.join("、")}`);
  }
  if (duplicateAnchors.length) {
    errors.push(`HTML 章節錨點重複：${duplicateAnchors.join("、")}`);
  }
  if (!missingAnchors.length && !unknownAnchors.length && !duplicateAnchors.length
      && JSON.stringify(htmlAnchors) !== JSON.stringify(SECTION_ANCHORS)) {
    errors.push(`HTML 章節錨點順序錯誤：${htmlAnchors.join(" → ")}`);
  }

  for (const block of spec.blocks) {
    const expected = BLOCK_SECTION.get(block.type);
    const region = normalize(htmlToText(audit.sectionText.get(expected) || ""));
    if (expected && !region.includes(normalize(block.title))) {
      errors.push(`HTML 把 ${block.type} 區塊「${block.title}」放錯章節，它屬於 ${expected}`);
    }
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
  console.log(JSON.stringify({ valid: true, sections: SECTION_ANCHORS, blocks: spec.blocks.length }, null, 2));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
