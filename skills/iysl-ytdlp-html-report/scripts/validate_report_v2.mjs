#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const BLOCK_TYPES = new Set(["narrative", "process", "comparison", "control-gap", "spotlight", "actions", "key-points", "food-for-thought"]);
const REQUIRED_READER_SECTIONS = [
  ["內容重述", new Set(["narrative", "process", "comparison", "control-gap", "spotlight"])],
  ["洞見", new Set(["key-points"])],
  ["food for thoughts", new Set(["food-for-thought"])],
  ["可行啟發", new Set(["actions"])],
];
const CLAIM_TYPES = new Set(["speaker_claim", "report_synthesis", "open_question"]);
// brief 的 claim 是一句判讀，不是懸而未決的問題，所以不接受 open_question。
const BRIEF_CLAIM_TYPES = new Set(["speaker_claim", "report_synthesis"]);
const TRANSCRIPT_KINDS = new Set(["native_captions", "auto_captions", "audio_asr"]);
const SALIENCE_SIGNALS = new Set([
  "concrete_metric", "decision", "counterintuitive_claim", "anecdote",
  "tradeoff", "specific_example", "product_image", "failure_or_recovery",
  "core_claim", "narrative_context", "caveat", "open_question",
]);
const LOCAL_PATH = /(?:file:\/\/|(?:^|[\s"'(])\/(?!\/)\S+|(?:^|[\s"'(])[A-Za-z]:[\\/]\S*)/i;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeMediaUrl(value) {
  if (!hasText(value)) return false;
  if (/^https?:\/\//i.test(value)) return isSafeHttpUrl(value);
  if (/^(?:file:|\/|[A-Za-z]:[\\/])/i.test(value) || value.includes("\\")) return false;
  if (value.split("/").includes("..")) return false;
  return /^[A-Za-z0-9._~!$&'()+,;=@%/-]+$/.test(value);
}

function isSafeHttpUrl(value) {
  if (!hasText(value) || /[\s\u0000-\u001f\u007f]/.test(value)) return false;
  try {
    const parsed = new URL(value);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
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

function collectRefs(value, into = new Set()) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectRefs(item, into));
  } else if (isObject(value)) {
    if (Array.isArray(value.evidence_refs)) value.evidence_refs.forEach((ref) => into.add(ref));
    Object.values(value).forEach((item) => collectRefs(item, into));
  }
  return into;
}

// 報告本身要花多久讀，是讀者決定要不要往下讀的第二個問題（第一個由 brief 回答）。
// 它完全由 spec 的讀者文字推導，所以不需要證據，但也不能是隨手填的數字：
// 驗證器算一次，spec 必須寫出同一個值。
export function readerCharacterCount(spec) {
  const parts = [];
  const walk = (value, key) => {
    if (typeof value === "string") {
      if (!["id", "type", "claim_type", "video_id", "url", "thumbnail_url", "transcript_kind", "language", "version", "duration", "channel"].includes(key)) {
        parts.push(value);
      }
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => walk(item, key));
      return;
    }
    if (isObject(value)) {
      for (const [childKey, child] of Object.entries(value)) {
        if (childKey === "evidence_refs") continue;
        walk(child, childKey);
      }
    }
  };
  walk(spec.brief, "brief");
  walk(spec.blocks, "blocks");
  walk(spec.title, "title");
  walk(spec.subtitle, "subtitle");
  return parts.join("").replace(/\s+/g, "").length;
}

export function readingMinutes(spec) {
  return Math.max(1, Math.ceil(readerCharacterCount(spec) / 350));
}

export function validateReportV2(spec, options = {}) {
  const errors = [];
  const transcript = typeof options.transcript === "string" ? options.transcript : "";
  const evidencePositions = new Map();
  const rootAllowed = ["version", "title", "subtitle", "language", "source", "reading_minutes", "brief", "evidence", "blocks", "topic_coverage"];
  if (!requireKeys(spec, rootAllowed, ["version", "title", "source", "reading_minutes", "brief", "evidence", "blocks", "topic_coverage"], "$", errors)) {
    return errors;
  }
  if (spec.version !== "2.3") errors.push("$.version 必須是 2.3");
  if (!hasText(spec.title)) errors.push("$.title 必須是非空字串");
  if ("subtitle" in spec && typeof spec.subtitle !== "string") errors.push("$.subtitle 必須是字串");
  if ("language" in spec && spec.language !== "zh-Hant") errors.push("$.language 必須是 zh-Hant");

  const sourceAllowed = ["video_id", "url", "channel", "duration", "thumbnail_url", "transcript_kind"];
  if (requireKeys(spec.source, sourceAllowed, ["video_id", "url", "transcript_kind"], "$.source", errors)) {
    if (!hasText(spec.source.video_id)) errors.push("$.source.video_id 必須是非空字串");
    if (!isSafeHttpUrl(spec.source.url)) {
      errors.push("$.source.url 必須是無空白、換行或憑證的 http(s) URL");
    }
    if ("thumbnail_url" in spec.source && !isSafeMediaUrl(spec.source.thumbnail_url)) {
      errors.push("$.source.thumbnail_url 必須是 http(s) URL 或不含 traversal 的安全相對路徑");
    }
    if (!TRANSCRIPT_KINDS.has(spec.source.transcript_kind)) {
      errors.push("$.source.transcript_kind 不受支援");
    }
  }

  const sectionTitleFor = new Map();
  for (const [title, types] of REQUIRED_READER_SECTIONS) {
    for (const type of types) sectionTitleFor.set(type, title);
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
      if (transcript && hasText(item.transcript_quote)) {
        const offset = transcript.indexOf(item.transcript_quote);
        if (offset < 0) errors.push(`${at}.transcript_quote 無法逐字回查 transcript`);
        else evidencePositions.set(item.id, offset / Math.max(1, transcript.length));
      }
      if (evidenceIds.has(item.id)) errors.push(`${at}.id 重複：${item.id}`);
      evidenceIds.add(item.id);
    });
  }

  const expectedMinutes = readingMinutes(spec);
  if (spec.reading_minutes !== expectedMinutes) {
    errors.push(`$.reading_minutes 必須是 ${expectedMinutes}（由讀者文字長度推導，不可自行填寫）`);
  }

  // 掃讀層和其他讀者主張受同一套證據治理：讀者最先看、也最可能只看的那一層，
  // 如果是唯一不受 evidence gate 管的一層，gate 就形同虛設。
  if (requireKeys(spec.brief, ["claim", "takeaways"], ["claim", "takeaways"], "$.brief", errors)) {
    if (requireKeys(spec.brief.claim, ["text", "claim_type", "evidence_refs"], ["text", "claim_type", "evidence_refs"], "$.brief.claim", errors)) {
      if (!hasText(spec.brief.claim.text)) errors.push("$.brief.claim.text 必須是非空字串");
      if (!BRIEF_CLAIM_TYPES.has(spec.brief.claim.claim_type)) {
        errors.push("$.brief.claim.claim_type 必須是 speaker_claim 或 report_synthesis");
      }
      validateRefs(spec.brief.claim.evidence_refs, "$.brief.claim.evidence_refs", evidenceIds, errors);
    }
    if (!Array.isArray(spec.brief.takeaways)) {
      errors.push("$.brief.takeaways 必須是陣列");
    } else if (spec.brief.takeaways.length < 3 || spec.brief.takeaways.length > 4) {
      errors.push("$.brief.takeaways 必須有三到四項");
    } else {
      validateItems(spec.brief.takeaways, "$.brief.takeaways", ["text", "evidence_refs"], ["text", "evidence_refs"], evidenceIds, errors);
    }
  }

  const blockIds = new Set();
  const blockRefs = new Map();
  if (!Array.isArray(spec.blocks) || spec.blocks.length === 0) {
    errors.push("$.blocks 必須至少有一個 adaptive block");
  } else {
    const presentBlockTypes = new Set();
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
      presentBlockTypes.add(block.type);
      const sectionTitle = sectionTitleFor.get(block.type);
      if (sectionTitle && typeof block.title === "string"
          && block.title.trim().toLowerCase() === sectionTitle.toLowerCase()) {
        errors.push(`${at}.title 不可與所屬章節同名：${sectionTitle}`);
      }
      const common = ["id", "type", "title", "summary", "claim_type", "evidence_refs"];
      const typeFields = {
        narrative: ["paragraphs"],
        process: ["nodes"],
        comparison: ["columns", "rows"],
        "control-gap": ["rows"],
        spotlight: ["angle", "items"],
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
      blockRefs.set(block.id, collectRefs(block));
      if (!CLAIM_TYPES.has(block.claim_type)) errors.push(`${at}.claim_type 不受支援`);
      validateRefs(block.evidence_refs, `${at}.evidence_refs`, evidenceIds, errors);

      if (block.type === "narrative") {
        validateItems(block.paragraphs, `${at}.paragraphs`, ["text", "evidence_refs"], ["text", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "process") {
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
      } else if (block.type === "spotlight") {
        if (!SALIENCE_SIGNALS.has(block.angle)) errors.push(`${at}.angle 不受支援`);
        validateItems(block.items, `${at}.items`, ["heading", "text", "evidence_refs"], ["heading", "text", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "actions") {
        validateItems(block.items, `${at}.items`, ["action", "when", "evidence_refs"], ["action", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "key-points") {
        validateItems(block.items, `${at}.items`, ["heading", "text", "evidence_refs"], ["heading", "text", "evidence_refs"], evidenceIds, errors);
      } else if (block.type === "food-for-thought") {
        validateItems(block.items, `${at}.items`, ["prompt", "context", "evidence_refs"], ["prompt", "evidence_refs"], evidenceIds, errors);
      }
    });
    for (const [sectionTitle, acceptedTypes] of REQUIRED_READER_SECTIONS) {
      if (![...acceptedTypes].some((type) => presentBlockTypes.has(type))) {
        errors.push(`$.blocks 缺少 reader-facing 章節：${sectionTitle}`);
      }
    }
  }

  if (requireKeys(spec.topic_coverage, ["sweep", "topics"], ["sweep", "topics"], "$.topic_coverage", errors)) {
    const topicIds = new Set();
    const topicById = new Map();
    if (!Array.isArray(spec.topic_coverage.topics) || spec.topic_coverage.topics.length === 0) {
      errors.push("$.topic_coverage.topics 必須至少有一個高顯著性 topic");
    } else {
      spec.topic_coverage.topics.forEach((topic, index) => {
        const at = `$.topic_coverage.topics[${index}]`;
        if (!requireKeys(topic, ["id", "title", "salience_signals", "evidence_refs", "block_ids"], ["id", "title", "salience_signals", "evidence_refs", "block_ids"], at, errors)) return;
        if (!hasText(topic.id)) errors.push(`${at}.id 必須是非空字串`);
        if (!hasText(topic.title)) errors.push(`${at}.title 必須是非空字串`);
        if (topicIds.has(topic.id)) errors.push(`${at}.id 重複：${topic.id}`);
        topicIds.add(topic.id);
        topicById.set(topic.id, topic);
        if (!Array.isArray(topic.salience_signals) || topic.salience_signals.length < 1) {
          errors.push(`${at}.salience_signals 必須至少有一個納入理由`);
        } else {
          const seen = new Set();
          topic.salience_signals.forEach((signal, signalIndex) => {
            if (!SALIENCE_SIGNALS.has(signal)) errors.push(`${at}.salience_signals[${signalIndex}] 不受支援：${signal}`);
            if (seen.has(signal)) errors.push(`${at}.salience_signals 不可重複：${signal}`);
            seen.add(signal);
          });
        }
        validateRefs(topic.evidence_refs, `${at}.evidence_refs`, evidenceIds, errors);
        if (!Array.isArray(topic.block_ids) || topic.block_ids.length === 0) {
          errors.push(`${at}.block_ids 必須至少映射一個 reader block`);
        } else {
          const mappedRefs = new Set();
          const seenBlocks = new Set();
          topic.block_ids.forEach((blockId, blockIndex) => {
            if (!hasText(blockId) || !blockIds.has(blockId)) errors.push(`${at}.block_ids[${blockIndex}] 指向不存在的 block：${blockId}`);
            if (seenBlocks.has(blockId)) errors.push(`${at}.block_ids 不可重複：${blockId}`);
            seenBlocks.add(blockId);
            for (const ref of blockRefs.get(blockId) || []) mappedRefs.add(ref);
          });
          for (const ref of topic.evidence_refs || []) {
            if (!mappedRefs.has(ref)) errors.push(`${at}.evidence_refs 的 ${ref} 沒有出現在映射的 reader block`);
          }
        }
      });
    }

    const swept = new Set();
    if (requireKeys(spec.topic_coverage.sweep, ["opening", "middle", "ending"], ["opening", "middle", "ending"], "$.topic_coverage.sweep", errors)) {
      for (const region of ["opening", "middle", "ending"]) {
        const ids = spec.topic_coverage.sweep[region];
        if (!Array.isArray(ids) || ids.length === 0) {
          errors.push(`$.topic_coverage.sweep.${region} 必須至少列出一個 topic`);
          continue;
        }
        const seen = new Set();
        ids.forEach((id, index) => {
          if (!hasText(id) || !topicById.has(id)) errors.push(`$.topic_coverage.sweep.${region}[${index}] 指向不存在的 topic：${id}`);
          if (seen.has(id)) errors.push(`$.topic_coverage.sweep.${region} 不可重複：${id}`);
          seen.add(id);
          swept.add(id);
          if (transcript && topicById.has(id)) {
            const [start, end] = {
              opening: [0, 0.34],
              middle: [0.25, 0.78],
              ending: [0.66, 1.01],
            }[region];
            const topic = topicById.get(id);
            const hasRegionalEvidence = (topic.evidence_refs || []).some((ref) => {
              const position = evidencePositions.get(ref);
              return Number.isFinite(position) && position >= start && position < end;
            });
            if (!hasRegionalEvidence) {
              errors.push(`$.topic_coverage.sweep.${region}[${index}] 的 ${id} 沒有來自 transcript ${region} 區段的 evidence`);
            }
          }
        });
      }
    }
    for (const id of topicIds) {
      if (!swept.has(id)) errors.push(`$.topic_coverage.topics 的 ${id} 沒有出現在 opening／middle／ending sweep`);
    }
  }

  validateReaderStrings(spec, "$", errors);
  return errors;
}

export function readAndValidateReportV2(inputPath, options = {}) {
  const spec = JSON.parse(readFileSync(inputPath, "utf8"));
  const errors = validateReportV2(spec, options);
  if (errors.length) throw new Error(`v2 report contract 驗證失敗：\n- ${errors.join("\n- ")}`);
  return spec;
}

function usage() {
  console.error("用法：validate_report_v2.mjs <report-v2.json> [--transcript <clean-transcript.md>] [--print-reading-minutes]");
  process.exit(2);
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const inputPath = process.argv[2] || usage();
  try {
    // reading_minutes 必須和推導值相符，所以要有一個正式的取值管道，
    // 而不是叫作者去猜或從錯誤訊息裡抄。
    if (process.argv.includes("--print-reading-minutes")) {
      console.log(String(readingMinutes(JSON.parse(readFileSync(inputPath, "utf8")))));
      process.exit(0);
    }
    const transcriptIndex = process.argv.indexOf("--transcript");
    const transcriptPath = transcriptIndex >= 0 ? process.argv[transcriptIndex + 1] : "";
    if (transcriptIndex >= 0 && !transcriptPath) usage();
    const spec = readAndValidateReportV2(inputPath, {
      transcript: transcriptPath ? readFileSync(transcriptPath, "utf8") : "",
    });
    console.log(JSON.stringify({ valid: true, version: spec.version, blocks: spec.blocks.length, topics: spec.topic_coverage.topics.length }, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
