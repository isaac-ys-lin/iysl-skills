#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

function usage(exitCode = 2) {
  console.error("用法：finalize_report.mjs --spec <report-v2.json> --manifest <source-manifest.json> --out-dir <run-dir> [--html-in <final.html> --presentation-backend <name>] [--fallback-reason <kami-unavailable|kami-not-selected>]");
  process.exit(exitCode);
}

function parseArgs(args) {
  const options = { spec: "", manifest: "", outDir: "", htmlIn: "", presentationBackend: "", fallbackReason: "" };
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    const value = args[index + 1];
    if (["--spec", "--manifest", "--out-dir", "--html-in", "--presentation-backend", "--fallback-reason"].includes(key)) {
      if (!value || value.startsWith("--")) usage();
      if (key === "--spec") options.spec = value;
      else if (key === "--manifest") options.manifest = value;
      else if (key === "--out-dir") options.outDir = value;
      else if (key === "--html-in") options.htmlIn = value;
      else if (key === "--presentation-backend") options.presentationBackend = value;
      else options.fallbackReason = value;
      index += 1;
    } else usage();
  }
  if (!options.spec || !options.manifest || !options.outDir) usage();
  // 外部出稿時不猜是誰產的：backend 必須指明，否則 sidecar 會記錄一個假的來源。
  if (options.htmlIn && !options.presentationBackend) {
    throw new Error("使用 --html-in 時必須以 --presentation-backend 指明出稿的 presentation backend");
  }
  if (options.htmlIn && options.presentationBackend === "built-in-v2") {
    throw new Error("--html-in 交付的不是內建輸出，presentation backend 不能標成 built-in-v2");
  }
  if (options.htmlIn && ["kami-unavailable", "kami-not-selected"].includes(options.fallbackReason)) {
    throw new Error("這次沒有走保底路徑，--fallback-reason 不能宣稱 fallback 發生過");
  }
  if (!options.htmlIn) {
    if (options.presentationBackend && options.presentationBackend !== "built-in-v2") {
      throw new Error("沒有 --html-in 時只會產生內建保底輸出，presentation backend 必須是 built-in-v2");
    }
    options.presentationBackend = "built-in-v2";
    // 保底路徑要說清楚是「Kami 不可用」還是「這次沒選 Kami」，兩種事故不能長成同一行紀錄。
    if (!options.fallbackReason) options.fallbackReason = "kami-not-selected";
    if (!["kami-unavailable", "kami-not-selected"].includes(options.fallbackReason)) {
      throw new Error("保底路徑的 --fallback-reason 必須是 kami-unavailable 或 kami-not-selected");
    }
  } else if (!options.fallbackReason) {
    options.fallbackReason = "not-applicable";
  }
  return options;
}

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function runNode(script, args) {
  const result = spawnSync(process.execPath, [path.join(SCRIPT_DIR, script), ...args], {
    encoding: "utf8",
    maxBuffer: 128 * 1024 * 1024,
  });
  if (result.status !== 0) {
    const detail = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
    throw new Error(detail || `${script} failed`);
  }
  return result.stdout;
}

function scalar(value, fallback = "not-provided") {
  if (value === undefined || value === null || String(value).trim() === "") return fallback;
  return String(value).replace(/[\r\n]+/g, " ").trim();
}

function sidecarValue(manifest, metadata, key, fallback) {
  return scalar(manifest[key] ?? metadata[key], fallback);
}

function buildSidecar({ manifest, metadata, spec, markdownPath, htmlPath, presentationBackend, fallbackReason, semanticWarnings }) {
  const id = scalar(manifest.id || spec.source.video_id);
  const sourceUrl = scalar(manifest.url || metadata.original_url || spec.source.url);
  const resolvedUrl = scalar(manifest.resolved_url || metadata.webpage_url || sourceUrl);
  const transcriptPath = scalar(manifest.transcript, "not-provided");
  const transcriptRegions = transcriptPath !== "not-provided" && existsSync(transcriptPath)
    ? "passed; transcript_regions=verified"
    : "not-run; transcript_regions=unavailable";
  const subtitleSource = manifest.subtitle
    ? scalar(manifest.subtitle_status, "available")
    : scalar(manifest.subtitle_status, "captions-unavailable");
  const coverage = spec.topic_coverage;
  const coverageSummary = ["opening", "middle", "ending"]
    .map((region) => `${region}=${coverage.sweep[region].length}`)
    .join(",");
  return [
    "# Verification",
    "",
    `- source_url: ${sourceUrl}`,
    `- resolved_url: ${resolvedUrl}`,
    `- video_id: ${id}`,
    `- metadata_path: ${scalar(manifest.metadata)}`,
    `- transcript_path: ${transcriptPath}`,
    `- report_markdown_path: ${markdownPath}`,
    `- report_html_path: ${htmlPath}`,
    `- presentation_backend: ${scalar(presentationBackend)}`,
    `- presentation_fallback_reason: ${scalar(fallbackReason)}`,
    `- topical_coverage_gate: ${transcriptRegions}; topics=${coverage.topics.length}; ${coverageSummary}`,
    ...(spec.version === "2.4" ? [
      `- semantic_completeness_gate: ${spec.completeness_review.status}; units=${spec.semantic_inventory.length}; interpretations=${spec.interpretations.length}`,
      `- source_scope: ${spec.source_limitation.scope}`,
      `- semantic_warnings: ${semanticWarnings.length ? semanticWarnings.join(" | ") : "none"}`,
    ] : []),
    `- subtitle_source: ${subtitleSource}`,
    `- extraction_tool: ${sidecarValue(manifest, metadata, "extraction_tool", "yt-dlp via extract_transcript.mjs")}`,
    `- transcription_method: ${sidecarValue(manifest, metadata, "transcription_method", "native captions")}`,
    `- asr_backend: ${sidecarValue(manifest, metadata, "asr_backend", "not-applicable")}`,
    `- asr_model: ${sidecarValue(manifest, metadata, "asr_model", "not-applicable")}`,
    `- asr_network_policy: ${sidecarValue(manifest, metadata, "asr_network_policy", "not-applicable")}`,
    `- transcript_normalization: ${sidecarValue(manifest, metadata, "transcript_normalization", "not-applicable")}`,
    `- audio_preprocess: ${sidecarValue(manifest, metadata, "audio_preprocess", "not-applicable")}`,
    `- audio_cache_path: ${sidecarValue(manifest, metadata, "audio_cache_path", "not-applicable")}`,
    `- extracted_at: ${sidecarValue(manifest, metadata, "extracted_at", new Date().toISOString())}`,
    "",
    "## Command Evidence",
    "",
    `- transcript_extract: ${scalar(manifest.prepared_by, "source manifest supplied")}`,
    "- html_render: render_report_v2.mjs passed",
    "- html_parse: basic HTML root/main contract passed",
    "- section_scan: validate_report_artifacts.mjs passed",
    "- deterministic_verification: v2 validator and artifact validator passed",
    "",
    "## Limits",
    "",
    "- The reader sees only the bounded transcript-only source notice; transcript quality, ASR, extraction, and verification details remain here for operators.",
    "",
  ].join("\n");
}

function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  const spec = readJson(options.spec);
  if (spec.version !== "2.4") {
    throw new Error("finalization 只建立 v2.4 新報告；v2.3 僅保留既有 artifact 驗證支援");
  }
  const manifest = readJson(options.manifest);
  const metadata = manifest.metadata && existsSync(manifest.metadata) ? readJson(manifest.metadata) : {};
  const videoId = scalar(manifest.id || spec.source.video_id, "video");
  const outDir = path.resolve(options.outDir);
  mkdirSync(outDir, { recursive: true });
  const markdownPath = path.join(outDir, `${videoId}.report.md`);
  const htmlPath = path.join(outDir, `${videoId}.report.html`);
  const sidecarPath = path.join(outDir, `${videoId}.verification.md`);

  // 上一次執行的殘骸會讓這次的失敗看起來像成功：同名的舊 HTML 還在，sidecar 卻
  // 已經換成這次的 backend。開工前先清掉這三份同名交付物。
  // 但外部出稿常常就寫在 htmlPath 上（SKILL.md 的 step 3 正是這樣叫的），
  // 那份檔案是這次執行的輸入，不是上一次的殘骸；清掉它等於在讀取前先毀掉它。
  const externalHtml = options.htmlIn ? path.resolve(options.htmlIn) : "";
  const deliverables = [markdownPath, htmlPath, sidecarPath];
  for (const file of deliverables) {
    if (path.resolve(file) === externalHtml) continue;
    if (existsSync(file)) rmSync(file);
  }

  const transcriptPath = typeof manifest.transcript === "string" && existsSync(manifest.transcript)
    ? manifest.transcript
    : "";
  if (!transcriptPath) {
    throw new Error("finalization 需要 source manifest 指向存在的 clean transcript；semantic completeness gate 不可略過");
  }
  const validation = JSON.parse(runNode("validate_report.mjs", [options.spec, ...(transcriptPath ? ["--transcript", transcriptPath] : [])]));
  // 外部出稿時完全不渲染內建 HTML：交給讀者的那一份，就是被驗的那一份。驗證
  // 未過之前不把它寫進 out-dir，失敗的執行不會留下一份看起來可用的交付物。
  if (externalHtml) {
    runNode("render_report_v2.mjs", ["--spec", options.spec, "--markdown-out", markdownPath]);
  } else {
    runNode("render_report_v2.mjs", ["--spec", options.spec, "--markdown-out", markdownPath, "--html-out", htmlPath]);
  }
  const validatedHtmlPath = externalHtml || htmlPath;
  const html = readFileSync(validatedHtmlPath, "utf8");
  const structuralProblems = [];
  if (!/<html\b/i.test(html) || !/<\/html>/i.test(html)) structuralProblems.push("缺少完整的 <html> 文件外殼");
  if (!/<main\b/i.test(html) || !/<\/main>/i.test(html)) structuralProblems.push("缺少 <main> 區塊");
  if (/<script\b/i.test(html)) structuralProblems.push("含有 <script>，最終報告不得內嵌腳本");
  if (structuralProblems.length) {
    throw new Error(`最終 HTML 未通過基本結構檢查：${structuralProblems.join("；")}`);
  }
  const sidecar = buildSidecar({
    manifest, metadata, spec, markdownPath, htmlPath,
    presentationBackend: options.presentationBackend,
    fallbackReason: options.fallbackReason,
    semanticWarnings: validation.warnings || [],
  });
  writeFileSync(sidecarPath, sidecar, "utf8");
  try {
    runNode("validate_report_artifacts.mjs", [
      "--spec", options.spec,
      "--markdown", markdownPath,
      "--html", validatedHtmlPath,
      "--sidecar", sidecarPath,
    ]);
  } catch (error) {
    // sidecar 的 Command Evidence 宣稱每一關都過了。驗證沒過就不能把它留下來
    // 當作那次執行的紀錄。
    for (const file of deliverables) {
      if (path.resolve(file) === externalHtml) continue;
      if (existsSync(file)) rmSync(file);
    }
    throw error;
  }
  if (externalHtml && path.resolve(htmlPath) !== externalHtml) {
    copyFileSync(externalHtml, htmlPath);
  }
  const result = {
    valid: true,
    video_id: videoId,
    report_markdown: markdownPath,
    report_html: htmlPath,
    verification_sidecar: sidecarPath,
    presentation_backend: options.presentationBackend,
  };
  console.log(JSON.stringify(result, null, 2));
  return result;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
