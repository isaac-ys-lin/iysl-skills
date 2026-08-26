#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import {
  readerCharacterCount,
  readingMinutes as readingMinutesV23,
  validateReportV2,
} from "./validate_report_v2.mjs";

const ROOT_FIELDS = [
  "version", "title", "subtitle", "language", "source", "reading_minutes", "brief",
  "evidence", "blocks", "topic_coverage", "semantic_inventory", "interpretations",
  "completeness_review", "source_limitation",
];
const REQUIRED_ROOT_FIELDS = ROOT_FIELDS.filter((field) => field !== "subtitle" && field !== "language");
const UNIT_KINDS = new Set(["claim", "context", "example", "metric", "decision", "tradeoff", "caveat", "question", "anecdote", "nonsemantic"]);
const DISPOSITIONS = new Set(["included", "compressed_duplicate", "excluded_nonsemantic"]);
const COGNITIVE_JOBS = new Set(["explain", "sequence", "compare", "control", "emphasize", "derive_insight", "raise_question", "prompt_action"]);
const INTERPRETATION_KINDS = new Set(["insight", "question", "action"]);
const REGIONS = ["opening", "middle", "ending"];
export const SOURCE_LIMITATION_NOTICE = "本報告以逐字稿為唯一內容來源，可能未涵蓋純畫面、語氣與示範細節；需要核對時請回到原影片。";

const hasText = (value) => typeof value === "string" && value.trim().length > 0;
const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

function requireKeys(value, allowed, required, at, errors) {
  if (!isObject(value)) {
    errors.push(`${at} 必須是物件`);
    return false;
  }
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) errors.push(`${at}.${key} 不受支援`);
  }
  for (const key of required) {
    if (!(key in value)) errors.push(`${at}.${key} 是必填`);
  }
  return true;
}

function uniqueTextArray(value, at, errors, { min = 0 } = {}) {
  if (!Array.isArray(value) || value.length < min) {
    errors.push(`${at} 必須是至少 ${min} 項的陣列`);
    return [];
  }
  const seen = new Set();
  value.forEach((item, index) => {
    if (!hasText(item)) errors.push(`${at}[${index}] 必須是非空字串`);
    if (seen.has(item)) errors.push(`${at} 不可重複：${item}`);
    seen.add(item);
  });
  return value;
}

function baseSpecForV23(spec) {
  const base = Object.fromEntries(Object.entries(spec || {}).filter(([key]) => ![
    "semantic_inventory", "interpretations", "completeness_review", "source_limitation",
  ].includes(key)));
  base.version = "2.3";
  base.reading_minutes = readingMinutesV23(base);
  return base;
}

export function readingMinutes(spec) {
  const base = baseSpecForV23(spec);
  const notice = hasText(spec?.source_limitation?.notice) ? spec.source_limitation.notice.trim() : "";
  return Math.max(1, Math.ceil((readerCharacterCount(base) + [...notice].length) / 450));
}

function evidencePositionMap(spec, transcript) {
  const positions = new Map();
  if (!hasText(transcript)) return positions;
  for (const evidence of spec.evidence || []) {
    const quote = evidence?.transcript_quote;
    if (!hasText(evidence?.id) || !hasText(quote)) continue;
    const position = transcript.indexOf(quote);
    if (position >= 0) positions.set(evidence.id, position / Math.max(1, transcript.length));
  }
  return positions;
}

export function validateReportV24(spec, options = {}) {
  const errors = [];
  if (!requireKeys(spec, ROOT_FIELDS, REQUIRED_ROOT_FIELDS, "$", errors)) return errors;
  if (spec.version !== "2.4") errors.push("$.version 必須是 2.4");

  const baseErrors = validateReportV2(baseSpecForV23(spec), options);
  errors.push(...baseErrors.filter((error) => !error.startsWith("$.reading_minutes")));
  const expectedMinutes = readingMinutes(spec);
  if (spec.reading_minutes !== expectedMinutes) {
    errors.push(`$.reading_minutes 必須由讀者內容推導為 ${expectedMinutes}`);
  }

  const evidenceIds = new Set((spec.evidence || []).map((item) => item.id));
  const blockById = new Map((spec.blocks || []).map((block) => [block.id, block]));
  const blockRefs = new Map((spec.blocks || []).map((block) => [block.id, new Set(block.evidence_refs || [])]));
  const unitById = new Map();

  if (!Array.isArray(spec.semantic_inventory) || spec.semantic_inventory.length === 0) {
    errors.push("$.semantic_inventory 必須至少有一個 unit");
  } else {
    spec.semantic_inventory.forEach((unit, index) => {
      const at = `$.semantic_inventory[${index}]`;
      const fields = ["id", "kind", "statement", "evidence_refs", "disposition", "duplicate_of", "cognitive_job", "primary_block_id", "secondary_block_ids", "routing_rationale"];
      if (!requireKeys(unit, fields, fields, at, errors)) return;
      if (!hasText(unit.id)) errors.push(`${at}.id 必須是非空字串`);
      if (unitById.has(unit.id)) errors.push(`${at}.id 重複：${unit.id}`);
      unitById.set(unit.id, unit);
      if (!UNIT_KINDS.has(unit.kind)) errors.push(`${at}.kind 不受支援`);
      if (!hasText(unit.statement)) errors.push(`${at}.statement 必須是非空字串`);
      const refs = uniqueTextArray(unit.evidence_refs, `${at}.evidence_refs`, errors, { min: 1 });
      refs.forEach((ref) => {
        if (!evidenceIds.has(ref)) errors.push(`${at}.evidence_refs 指向不存在的 evidence：${ref}`);
      });
      if (!DISPOSITIONS.has(unit.disposition)) errors.push(`${at}.disposition 不受支援`);
      if (!hasText(unit.routing_rationale)) errors.push(`${at}.routing_rationale 必須說明處置或 routing 理由`);
      const secondary = uniqueTextArray(unit.secondary_block_ids, `${at}.secondary_block_ids`, errors);

      if (unit.disposition === "included") {
        if (unit.kind === "nonsemantic") errors.push(`${at} included unit 不可標成 nonsemantic`);
        if (unit.duplicate_of !== null) errors.push(`${at}.duplicate_of 在 included 時必須是 null`);
        if (!COGNITIVE_JOBS.has(unit.cognitive_job)) errors.push(`${at}.cognitive_job 不受支援`);
        if (!hasText(unit.primary_block_id) || !blockById.has(unit.primary_block_id)) {
          errors.push(`${at}.primary_block_id 必須指向存在的 reader block`);
        }
        if (secondary.includes(unit.primary_block_id)) errors.push(`${at}.secondary_block_ids 不可重複 primary block`);
        secondary.forEach((id) => {
          if (!blockById.has(id)) errors.push(`${at}.secondary_block_ids 指向不存在的 block：${id}`);
        });
        const mappedRefs = new Set([unit.primary_block_id, ...secondary].flatMap((id) => [...(blockRefs.get(id) || [])]));
        refs.forEach((ref) => {
          if (!mappedRefs.has(ref)) errors.push(`${at}.evidence_refs 的 ${ref} 沒有出現在映射的 reader block`);
        });
      } else if (unit.disposition === "compressed_duplicate") {
        if (!hasText(unit.duplicate_of)) errors.push(`${at}.duplicate_of 在 compressed_duplicate 時必填`);
        if (unit.cognitive_job !== null || unit.primary_block_id !== null || secondary.length) {
          errors.push(`${at} compressed_duplicate 不可另行 routing`);
        }
      } else if (unit.disposition === "excluded_nonsemantic") {
        if (unit.kind !== "nonsemantic") errors.push(`${at} 有效語意不可標成 excluded_nonsemantic`);
        if (unit.duplicate_of !== null || unit.cognitive_job !== null || unit.primary_block_id !== null || secondary.length) {
          errors.push(`${at} excluded_nonsemantic 不可另行 routing`);
        }
      }
    });
  }

  for (const [id, unit] of unitById) {
    if (unit.disposition !== "compressed_duplicate") continue;
    const seen = new Set([id]);
    let cursor = unit.duplicate_of;
    while (hasText(cursor)) {
      if (seen.has(cursor)) {
        errors.push(`$.semantic_inventory 的 duplicate chain 形成循環：${[...seen, cursor].join(" → ")}`);
        break;
      }
      seen.add(cursor);
      const target = unitById.get(cursor);
      if (!target) {
        errors.push(`$.semantic_inventory 的 duplicate_of 指向不存在的 unit：${cursor}`);
        break;
      }
      if (target.disposition === "included") break;
      if (target.disposition !== "compressed_duplicate") {
        errors.push(`$.semantic_inventory 的 duplicate chain 必須落到 included unit：${cursor}`);
        break;
      }
      cursor = target.duplicate_of;
    }
  }

  const includedUnits = [...unitById.values()].filter((unit) => unit.disposition === "included");
  const includedEvidence = new Set(includedUnits.flatMap((unit) => unit.evidence_refs || []));
  const readerBlockEvidence = new Set((spec.blocks || []).flatMap((block) => block.evidence_refs || []));
  for (const ref of [spec.brief?.claim, ...(spec.brief?.takeaways || [])].flatMap((item) => item?.evidence_refs || [])) {
    if (!includedEvidence.has(ref)) errors.push(`$.brief 的 ${ref} 沒有來自 included semantic unit`);
    if (!readerBlockEvidence.has(ref)) errors.push(`$.brief 的 ${ref} 沒有正式 reader block 去向`);
  }

  for (const topic of spec.topic_coverage?.topics || []) {
    const topicBlocks = new Set(topic.block_ids || []);
    for (const ref of topic.evidence_refs || []) {
      const closed = includedUnits.some((unit) =>
        (unit.evidence_refs || []).includes(ref)
        && [unit.primary_block_id, ...(unit.secondary_block_ids || [])].some((id) => topicBlocks.has(id))
      );
      if (!closed) errors.push(`$.topic_coverage 的 ${topic.id}/${ref} 沒有由 semantic inventory 閉合到 reader block`);
    }
  }
  for (const unit of includedUnits) {
    const closed = (spec.topic_coverage?.topics || []).some((topic) =>
      (topic.evidence_refs || []).some((ref) => (unit.evidence_refs || []).includes(ref))
      && (topic.block_ids || []).some((id) => [unit.primary_block_id, ...(unit.secondary_block_ids || [])].includes(id))
    );
    if (!closed) errors.push(`$.semantic_inventory 的 ${unit.id} 沒有 topic_coverage 去向`);
  }

  const interpretationIds = new Set();
  const interpretedBlocks = new Set();
  if (!Array.isArray(spec.interpretations)) {
    errors.push("$.interpretations 必須是陣列");
  } else {
    spec.interpretations.forEach((item, index) => {
      const at = `$.interpretations[${index}]`;
      const fields = ["id", "kind", "text", "basis_unit_ids", "block_ids"];
      if (!requireKeys(item, fields, fields, at, errors)) return;
      if (!hasText(item.id)) errors.push(`${at}.id 必須是非空字串`);
      if (interpretationIds.has(item.id)) errors.push(`${at}.id 重複：${item.id}`);
      interpretationIds.add(item.id);
      if (!INTERPRETATION_KINDS.has(item.kind)) errors.push(`${at}.kind 不受支援`);
      if (!hasText(item.text)) errors.push(`${at}.text 必須是非空字串`);
      const basisIds = uniqueTextArray(item.basis_unit_ids, `${at}.basis_unit_ids`, errors, { min: 1 });
      const mappedBlocks = uniqueTextArray(item.block_ids, `${at}.block_ids`, errors, { min: 1 });
      const mappedRefs = new Set(mappedBlocks.flatMap((id) => [...(blockRefs.get(id) || [])]));
      mappedBlocks.forEach((id) => {
        const block = blockById.get(id);
        if (!block) errors.push(`${at}.block_ids 指向不存在的 block：${id}`);
        else if (block.claim_type === "speaker_claim") errors.push(`${at}.block_ids 不可把 interpretation 放進 speaker_claim：${id}`);
        interpretedBlocks.add(id);
      });
      basisIds.forEach((id) => {
        const unit = unitById.get(id);
        if (!unit || unit.disposition !== "included") errors.push(`${at}.basis_unit_ids 必須指向 included unit：${id}`);
        else if (!(unit.evidence_refs || []).some((ref) => mappedRefs.has(ref))) {
          errors.push(`${at} 的 basis unit ${id} 沒有 evidence 出現在 interpretation block`);
        }
      });
    });
  }
  for (const block of spec.blocks || []) {
    if (block.claim_type === "report_synthesis" && !interpretedBlocks.has(block.id)) {
      errors.push(`$.blocks 的推導區塊 ${block.id} 沒有 interpretation`);
    }
  }

  if (requireKeys(spec.completeness_review, ["status", "sweep"], ["status", "sweep"], "$.completeness_review", errors)) {
    if (spec.completeness_review.status !== "passed") errors.push("$.completeness_review.status 必須是 passed");
    const swept = new Set();
    const positions = evidencePositionMap(spec, options.transcript || "");
    if (requireKeys(spec.completeness_review.sweep, REGIONS, REGIONS, "$.completeness_review.sweep", errors)) {
      for (const region of REGIONS) {
        const ids = uniqueTextArray(spec.completeness_review.sweep[region], `$.completeness_review.sweep.${region}`, errors);
        const [start, end] = { opening: [0, 0.34], middle: [0.25, 0.78], ending: [0.66, 1.01] }[region];
        ids.forEach((id) => {
          const unit = unitById.get(id);
          if (!unit) errors.push(`$.completeness_review.sweep.${region} 指向不存在的 unit：${id}`);
          else {
            swept.add(id);
            if (positions.size && !(unit.evidence_refs || []).some((ref) => {
              const position = positions.get(ref);
              return Number.isFinite(position) && position >= start && position < end;
            })) errors.push(`$.completeness_review.sweep.${region} 的 ${id} 沒有來自 transcript ${region} 區段的 evidence`);
          }
        });
      }
    }
    for (const [id, unit] of unitById) {
      if (unit.disposition !== "excluded_nonsemantic" && !swept.has(id)) {
        errors.push(`$.semantic_inventory 的 ${id} 沒有出現在 completeness review sweep`);
      }
    }
  }

  if (requireKeys(spec.source_limitation, ["scope", "notice"], ["scope", "notice"], "$.source_limitation", errors)) {
    if (spec.source_limitation.scope !== "transcript_only") errors.push("$.source_limitation.scope 必須是 transcript_only");
    if (spec.source_limitation.notice !== SOURCE_LIMITATION_NOTICE) {
      errors.push("$.source_limitation.notice 必須使用固定警語，完整明示逐字稿邊界與畫面、語氣、示範盲點");
    }
  }
  return errors;
}

export function reportWarnings(spec) {
  const warnings = [];
  const allowedTypes = new Map([
    ["explain", new Set(["narrative"])],
    ["sequence", new Set(["process"])],
    ["compare", new Set(["comparison"])],
    ["control", new Set(["control-gap"])],
    ["emphasize", new Set(["spotlight", "key-points"])],
    ["derive_insight", new Set(["food-for-thought"])],
    ["raise_question", new Set(["food-for-thought"])],
    ["prompt_action", new Set(["actions"])],
  ]);
  const blockType = new Map((spec.blocks || []).map((block) => [block.id, block.type]));
  const included = (spec.semantic_inventory || []).filter((unit) => unit.disposition === "included");
  const routingExceptions = included.filter((unit) => {
    const allowed = allowedTypes.get(unit.cognitive_job);
    return allowed && !allowed.has(blockType.get(unit.primary_block_id));
  });
  if (routingExceptions.length) {
    warnings.push(`routing exception: ${routingExceptions.length} unit(s) use a non-default primary block; review routing_rationale`);
  }
  const secondaryCount = included.reduce((sum, unit) => sum + (unit.secondary_block_ids || []).length, 0);
  if (included.length && secondaryCount > included.length) {
    warnings.push(`secondary duplication: ${secondaryCount} secondary mappings across ${included.length} included units`);
  }
  const recap = (spec.blocks || []).filter((block) => ["narrative", "process", "comparison", "control-gap", "spotlight"].includes(block.type));
  const narrativeCount = recap.filter((block) => block.type === "narrative").length;
  if (recap.length >= 3 && narrativeCount / recap.length > 0.7) {
    warnings.push(`narrative concentration: ${narrativeCount}/${recap.length} recap blocks are narrative`);
  }
  const duration = String(spec.source?.duration || "").match(/^(?:(\d+):)?(\d+):(\d+)$/);
  const videoMinutes = duration
    ? (Number(duration[1] || 0) * 60) + Number(duration[2]) + (Number(duration[3]) / 60)
    : 0;
  if (spec.reading_minutes > 30 || (videoMinutes > 0 && spec.reading_minutes > videoMinutes * 0.75)) {
    warnings.push(`reading burden: ${spec.reading_minutes} reader minutes for ${videoMinutes ? videoMinutes.toFixed(1) : "unknown"} video minutes`);
  }
  return warnings;
}

export function readAndValidateReportV24(inputPath, options = {}) {
  const spec = JSON.parse(readFileSync(inputPath, "utf8"));
  const errors = validateReportV24(spec, options);
  if (errors.length) throw new Error(`v2.4 report contract 驗證失敗：\n- ${errors.join("\n- ")}`);
  return spec;
}

function usage() {
  console.error("用法：validate_report_v2_4.mjs <report-v2.4.json> [--transcript <clean-transcript.md>] [--print-reading-minutes]");
  process.exit(2);
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const inputPath = process.argv[2] || usage();
  try {
    const raw = JSON.parse(readFileSync(inputPath, "utf8"));
    if (process.argv.includes("--print-reading-minutes")) {
      console.log(String(readingMinutes(raw)));
      process.exit(0);
    }
    const transcriptIndex = process.argv.indexOf("--transcript");
    const transcriptPath = transcriptIndex >= 0 ? process.argv[transcriptIndex + 1] : "";
    if (transcriptIndex >= 0 && !transcriptPath) usage();
    const spec = readAndValidateReportV24(inputPath, {
      transcript: transcriptPath ? readFileSync(transcriptPath, "utf8") : "",
    });
    console.log(JSON.stringify({
      valid: true,
      version: spec.version,
      blocks: spec.blocks.length,
      topics: spec.topic_coverage.topics.length,
      semantic_units: spec.semantic_inventory.length,
      interpretations: spec.interpretations.length,
      warnings: reportWarnings(spec),
    }, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
