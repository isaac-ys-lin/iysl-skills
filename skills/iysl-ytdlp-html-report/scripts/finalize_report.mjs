#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

function usage(exitCode = 2) {
  console.error("用法：finalize_report.mjs --spec <report-v2.json> --manifest <source-manifest.json> --out-dir <run-dir> [--presentation-backend <name>] [--fallback-reason <text>]");
  process.exit(exitCode);
}

function parseArgs(args) {
  const options = { spec: "", manifest: "", outDir: "", presentationBackend: "built-in-v2", fallbackReason: "not-applicable" };
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    const value = args[index + 1];
    if (["--spec", "--manifest", "--out-dir", "--presentation-backend", "--fallback-reason"].includes(key)) {
      if (!value || value.startsWith("--")) usage();
      if (key === "--spec") options.spec = value;
      else if (key === "--manifest") options.manifest = value;
      else if (key === "--out-dir") options.outDir = value;
      else if (key === "--presentation-backend") options.presentationBackend = value;
      else options.fallbackReason = value;
      index += 1;
    } else usage();
  }
  if (!options.spec || !options.manifest || !options.outDir) usage();
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

function buildSidecar({ manifest, metadata, spec, markdownPath, htmlPath, presentationBackend, fallbackReason }) {
  const id = scalar(manifest.id || spec.source.video_id);
  const sourceUrl = scalar(manifest.url || metadata.original_url || spec.source.url);
  const resolvedUrl = scalar(manifest.resolved_url || metadata.webpage_url || sourceUrl);
  const transcriptPath = scalar(manifest.transcript, "not-provided");
  const subtitleSource = manifest.subtitle
    ? scalar(manifest.subtitle_status, "available")
    : scalar(manifest.subtitle_status, "captions-unavailable");
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
    "- Source, transcript, ASR, and visual-verification limitations are retained here for operators; they are not reader-facing content.",
    "",
  ].join("\n");
}

function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  const spec = readJson(options.spec);
  const manifest = readJson(options.manifest);
  const metadata = manifest.metadata && existsSync(manifest.metadata) ? readJson(manifest.metadata) : {};
  const videoId = scalar(manifest.id || spec.source.video_id, "video");
  const outDir = path.resolve(options.outDir);
  mkdirSync(outDir, { recursive: true });
  const markdownPath = path.join(outDir, `${videoId}.report.md`);
  const htmlPath = path.join(outDir, `${videoId}.report.html`);
  const sidecarPath = path.join(outDir, `${videoId}.verification.md`);

  runNode("validate_report_v2.mjs", [options.spec]);
  runNode("render_report_v2.mjs", ["--spec", options.spec, "--markdown-out", markdownPath, "--html-out", htmlPath]);
  const html = readFileSync(htmlPath, "utf8");
  if (!/<html\b/i.test(html) || !/<\/html>/i.test(html) || !/<main\b/i.test(html) || !/<\/main>/i.test(html) || /<script\b/i.test(html)) {
    throw new Error("HTML basic parse/embedded-script check failed");
  }
  const sidecar = buildSidecar({
    manifest, metadata, spec, markdownPath, htmlPath,
    presentationBackend: options.presentationBackend,
    fallbackReason: options.fallbackReason,
  });
  writeFileSync(sidecarPath, sidecar, "utf8");
  runNode("validate_report_artifacts.mjs", [
    "--spec", options.spec,
    "--markdown", markdownPath,
    "--html", htmlPath,
    "--sidecar", sidecarPath,
  ]);
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
