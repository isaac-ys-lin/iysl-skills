#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const BLOCK_TYPES = new Set(["process", "comparison", "control-gap", "actions", "key-points", "food-for-thought"]);
const CLAIM_TYPES = new Set(["speaker_claim", "report_synthesis", "open_question"]);
const TRANSCRIPT_KINDS = new Set(["native_captions", "auto_captions", "audio_asr"]);
const LOCAL_PATH = /(?:file:\/\/|(?:^|[\s"'(])\/(?!\/)\S+|(?:^|[\s"'(])[A-Za-z]:[\\/]\S*)/i;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeMediaUrl(value) {
  if (!hasText(value)) return false;
  if (/^https?:\/\//i.test(value)) return true;
  if (/^(?:file:|\/|[A-Za-z]:[\\/])/i.test(value) || value.includes("\\")) return false;
  if (value.split("/").includes("..")) return false;
  return /^[A-Za-z0-9._~!$&'()+,;=@%/-]+$/.test(value);
}

function requireKeys(object, allowed, required, at, errors) {
  if (!isObject(object)) {
    errors.push(`${at} 必須是 object`);
    return false;
  }
  for (const key of required) {
    if (!(key in object)) errors.push(`${at}.${key} 為必填`);
  }
  for (const key of Object.keys(object)) {
    if (!allowed.includes(key)) errors.push(`${at}.${key} 不在 v2 contract`);
  }
  return true;
}

function validateRefs(refs, at, evidenceIds, errors) {
  if (!Array.isArray(refs) || refs.length === 0) {
    errors.push(`${at} 必須至少有一個 evidence ref`);
    return;
  }
  const seen = new Set();
  refs.forEach((ref, index) => {
    if (!hasText(ref)) errors.push(`${at}[${index}] 必須是非空字串`);
    else if (!evidenceIds.has(ref)) errors.push(`${at}[${index}] 指向不存在的 evidence：${ref}`);
    if (seen.has(ref)) errors.push(`${at} 不可重複引用 ${ref}`);
    seen.add(ref);
  });
}

function validateReaderStrings(value, at, errors) {
  if (typeof value === "string" && LOCAL_PATH.test(value)) {
    errors.push(`${at} 含禁止的 file:// 或絕對本機路徑`);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => validateReaderStrings(item, `${at}[${index}]`, errors));
  } else if (isObject(value)) {
    for (const [key, item] of Object.entries(value)) {
      validateReaderStrings(item, `${at}.${key}`, errors);
    }
  }
}

function validateItems(items, at, allowed, required, evidenceIds, errors) {
  if (!Array.isArray(items) || items.length === 0) {
    errors.push(`${at} 必須至少有一項`);
    return;
  }
  items.forEach((item, index) => {
    const itemAt = `${at}[${index}]`;
    if (!requireKeys(item, allowed, required, itemAt, errors)) return;
    for (const key of required.filter((key) => key !== "evidence_refs" && key !== "values")) {
      if (!hasText(item[key])) errors.push(`${itemAt}.${key} 必須是非空字串`);
    }
    validateRefs(item.evidence_refs, `${itemAt}.evidence_refs`, evidenceIds, errors);
  });
}

export function validateReportV2(spec) {
  const errors = [];
  const rootAllowed = ["version", "title", "subtitle", "language", "source", "evidence", "blocks"];
  if (!requireKeys(spec, rootAllowed, ["version", "title", "source", "evidence", "blocks"], "$", errors)) {
    return errors;
  }
  if (spec.version !== "2.0") errors.push("$.version 必須是 2.0");
  if (!hasText(spec.title)) errors.push("$.title 必須是非空字串");
  if ("subtitle" in spec && typeof spec.subtitle !== "string") errors.push("$.subtitle 必須是字串");
  if ("language" in spec && spec.language !== "zh-Hant") errors.push("$.language 必須是 zh-Hant");

  const sourceAllowed = ["video_id", "url", "channel", "duration", "thumbnail_url", "transcript_kind"];
  if (requireKeys(spec.source, sourceAllowed, ["video_id", "url", "transcript_kind"], "$.source", errors)) {
    if (!hasText(spec.source.video_id)) errors.push("$.source.video_id 必須是非空字串");
    if (!hasText(spec.source.url) || !/^https?:\/\//i.test(spec.source.url)) {
      errors.push("$.source.url 必須是 http(s) URL");
    }
    if ("thumbnail_url" in spec.source && !isSafeMediaUrl(spec.source.thumbnail_url)) {
      errors.push("$.source.thumbnail_url 必須是 http(s) URL 或不含 traversal 的安全相對路徑");
    }
    if (!TRANSCRIPT_KINDS.has(spec.source.transcript_kind)) {
      errors.push("$.source.transcript_kind 不受支援");
    }
  }

  const evidenceIds = new Set();
  if (!Array.isArray(spec.evidence) || spec.evidence.length === 0) {
    errors.push("$.evidence 必須至少有一筆逐字稿證據");
  } else {
    spec.evidence.forEach((item, index) => {
      const at = `$.evidence[${index}]`;
      if (!requireKeys(item, ["id", "transcript_quote", "timestamp"], ["id", "transcript_quote"], at, errors)) return;
      if (!hasText(item.id)) errors.push(`${at}.id 必須是非空字串`);
      if (!hasText(item.transcript_quote)) errors.push(`${at}.transcript_quote 必須是非空字串`);
      if (evidenceIds.has(item.id)) errors.push(`${at}.id 重複：${item.id}`);
      evidenceIds.add(item.id);
    });
  }

  if (!Array.isArray(spec.blocks) || spec.blocks.length === 0) {
    errors.push("$.blocks 必須至少有一個 adaptive block");
  } else {
    const blockIds = new Set();
    spec.blocks.forEach((block, index) => {
      const at = `$.blocks[${index}]`;
      if (!isObject(block)) {
        errors.push(`${at} 必須是 object`);
        return;
      }
      if (!BLOCK_TYPES.has(block.type)) {
        errors.push(`${at}.type 不受支援；v2 first slice 禁止 chart`);
        return;
      }
      const common = ["id", "type", "title", "summary", "claim_type", "evidence_refs"];
      const typeFields = {
        process: ["nodes"],
        comparison: ["columns", "rows"],
        "control-gap": ["rows"],
        actions: ["items"],
        "key-points": ["items"],
        "food-for-thought": ["items"],
      }[block.type];
      if (!requireKeys(block, [...common, ...typeFields], ["id", "type", "title", "claim_type", "evidence_refs", ...typeFields], at, errors)) return;
      for (const key of ["id", "title"]) {
        if (!hasText(block[key])) errors.push(`${at}.${key} 必須是非空字串`);
      }
      if (blockIds.has(block.id)) errors.push(`${at}.id 重複：${block.id}`);
      blockIds.add(block.id);
      if (!CLAIM_TYPES.has(block.claim_type)) errors.push(`${at}.claim_type 不受支援`);
      validateRefs(block.evidence_refs, `${at}.evidence_refs`, evidenceIds, errors);

      if (block.type === "process") {
        validateItems(block.nodes, `${at}.nodes`, ["label", "detail", "evidence_refs"], ["label", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "comparison") {
        if (!Array.isArray(block.columns) || block.columns.length < 2 || block.columns.some((value) => !hasText(value))) {
          errors.push(`${at}.columns 必須至少有兩個非空欄位`);
        }
        validateItems(block.rows, `${at}.rows`, ["label", "values", "evidence_refs"], ["label", "values", "evidence_refs"], evidenceIds, errors);
        if (Array.isArray(block.rows)) {
          block.rows.forEach((row, rowIndex) => {
            if (!Array.isArray(row.values) || row.values.length !== block.columns?.length || row.values.some((value) => typeof value !== "string")) {
              errors.push(`${at}.rows[${rowIndex}].values 必須與 columns 等長且全為字串`);
            }
          });
        }
      } else if (block.type === "control-gap") {
        validateItems(block.rows, `${at}.rows`, ["control", "observed", "gap", "evidence_refs"], ["control", "observed", "gap", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "actions") {
        validateItems(block.items, `${at}.items`, ["action", "when", "evidence_refs"], ["action", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "key-points") {
        validateItems(block.items, `${at}.items`, ["heading", "text", "evidence_refs"], ["heading", "text", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "food-for-thought") {
        validateItems(block.items, `${at}.items`, ["prompt", "context", "evidence_refs"], ["prompt", "evidence_refs"], evidenceIds, errors);
      }
    });
  }

  validateReaderStrings(spec, "$", errors);
  return errors;
}

export function readAndValidateReportV2(inputPath) {
  const spec = JSON.parse(readFileSync(inputPath, "utf8"));
  const errors = validateReportV2(spec);
  if (errors.length) throw new Error(`v2 report contract 驗證失敗：\n- ${errors.join("\n- ")}`);
  return spec;
}

function usage() {
  console.error("用法：validate_report_v2.mjs <report-v2.json>");
  process.exit(2);
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const inputPath = process.argv[2] || usage();
  try {
    const spec = readAndValidateReportV2(inputPath);
    console.log(JSON.stringify({ valid: true, version: spec.version, blocks: spec.blocks.length }, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
