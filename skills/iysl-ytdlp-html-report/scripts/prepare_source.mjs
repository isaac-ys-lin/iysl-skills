#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_MODEL = "Qwen/Qwen3-ASR-1.7B";

export function isSupportedPublicVideoUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return false;
  }
  if (!/^https?:$/.test(parsed.protocol) || parsed.username || parsed.password) return false;
  const host = parsed.hostname.toLowerCase();
  if (["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"].includes(host)) {
    const isWatch = parsed.pathname === "/watch" && parsed.searchParams.has("v");
    const isPathVideo = /^\/(?:shorts|embed|live)\/[^/]+$/.test(parsed.pathname);
    return (isWatch || isPathVideo) && !parsed.searchParams.has("list");
  }
  if (host === "youtu.be") return /^\/[^/]+$/.test(parsed.pathname) && !parsed.searchParams.has("list");
  if (host === "t.co" || host === "x.com" || host === "www.x.com" || host === "twitter.com" || host === "www.twitter.com") {
    return /^\/[^/]+/.test(parsed.pathname);
  }
  return false;
}

export function buildSourceManifest({
  id,
  url,
  metadataPath,
  transcriptPath = null,
  subtitlePath = null,
  captureStatus,
  asr = null,
}) {
  return {
    id,
    url,
    metadata: metadataPath,
    transcript: transcriptPath,
    subtitle: subtitlePath,
    capture_status: captureStatus,
    subtitle_status: subtitlePath ? "available" : "unavailable",
    ...(asr ? {
      transcription_method: asr.method || "local ASR",
      asr_backend: asr.backend || "unknown",
      asr_model: asr.model || "unknown",
      asr_network_policy: asr.networkPolicy || "unknown",
      transcript_normalization: asr.normalization || "unknown",
      audio_cache_path: asr.audioPath || "not-applicable",
    } : {}),
  };
}

function usage(exitCode = 2) {
  console.error([
    "用法：prepare_source.mjs <公開單支影片 URL> --out-dir <run-dir> [--asr auto|local-qwen|none]",
    "選項：--model <model>、--allow-model-download、--no-opencc",
    "prepare_source 不接受 cookies-from-browser，也不讀取 browser credentials。",
  ].join("\n"));
  process.exit(exitCode);
}

function parseArgs(args) {
  if (!args[0] || args[0].startsWith("-")) usage();
  const options = {
    url: args[0],
    outDir: "video-report-run",
    asr: "auto",
    model: DEFAULT_MODEL,
    allowModelDownload: false,
    noOpencc: false,
  };
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (["--cookies-from-browser", "--cookies", "--browser-cookies"].includes(arg)) {
      throw new Error("未授權的 browser cookies 存取被拒絕；prepare_source 不會自動讀取登入狀態。");
    }
    if (arg === "--out-dir") options.outDir = args[++index] || usage();
    else if (arg === "--asr") options.asr = args[++index] || usage();
    else if (arg === "--model") options.model = args[++index] || usage();
    else if (arg === "--allow-model-download") options.allowModelDownload = true;
    else if (arg === "--no-opencc") options.noOpencc = true;
    else usage();
  }
  if (!["auto", "local-qwen", "none"].includes(options.asr)) usage();
  return options;
}

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    maxBuffer: 128 * 1024 * 1024,
    ...options,
  });
  return result;
}

function findManifest(outDir) {
  const candidates = readdirSync(outDir)
    .filter((file) => file.endsWith(".manifest.json"))
    .map((file) => path.join(outDir, file));
  if (!candidates.length) return null;
  return candidates.sort()[candidates.length - 1];
}

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function failProcess(result, fallback) {
  const detail = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
  throw new Error(detail || fallback);
}

function prepareWithCaptions(options, manifestPath) {
  const manifest = readJson(manifestPath);
  return {
    ...manifest,
    prepared_by: "prepare_source.mjs",
    capture_status: manifest.capture_status || "captions-ready",
  };
}

function prepareWithLocalQwen(options, manifestPath) {
  const manifest = readJson(manifestPath);
  const outDir = path.dirname(manifestPath);
  const audioDir = path.join(outDir, "audio");
  mkdirSync(audioDir, { recursive: true });
  const audioTemplate = path.join(audioDir, `${manifest.id}.%(ext)s`);
  const download = run("yt-dlp", [
    "--no-playlist", "--concurrent-fragments", "8", "--no-progress",
    "--format", "bestaudio[abr<=64]/bestaudio",
    "--output", audioTemplate, options.url,
  ]);
  if (download.status !== 0) failProcess(download, "音訊下載失敗；請檢查 network、yt-dlp 或影片可用性。");
  const audioFile = readdirSync(audioDir)
    .filter((file) => file.startsWith(`${manifest.id}.`) && !file.endsWith(".part"))
    .map((file) => path.join(audioDir, file))
    .find((file) => existsSync(file));
  if (!audioFile) throw new Error("音訊下載完成但找不到音訊檔。");

  const transcriptPath = path.join(outDir, "transcripts", `${manifest.id}.clean-transcript.md`);
  const qwenArgs = [
    path.join(SCRIPT_DIR, "transcribe_local_qwen.mjs"),
    "--audio", audioFile,
    "--out", transcriptPath,
    "--model", options.model,
  ];
  if (options.noOpencc) qwenArgs.push("--no-opencc");
  if (options.allowModelDownload) qwenArgs.push("--allow-model-download");
  const transcribe = run(process.execPath, qwenArgs);
  if (transcribe.status !== 0) failProcess(transcribe, "無字幕且本機 Qwen3-ASR 不可用。");
  let asrSummary;
  try {
    asrSummary = JSON.parse(transcribe.stdout);
  } catch {
    throw new Error("ASR wrapper 沒有回傳可解析的 machine-readable summary。");
  }

  const metadataPath = path.resolve(manifest.metadata);
  const metadata = readJson(metadataPath);
  metadata.subtitle_status = "unavailable";
  metadata.transcription_method = `${asrSummary.backend} ${asrSummary.model}`;
  metadata.asr_backend = asrSummary.backend;
  metadata.asr_model = asrSummary.model;
  metadata.asr_network_policy = asrSummary.model_network_policy;
  metadata.transcript_normalization = asrSummary.normalization;
  writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
  const prepared = buildSourceManifest({
    id: manifest.id,
    url: manifest.url || options.url,
    metadataPath,
    transcriptPath,
    subtitlePath: null,
    captureStatus: "audio-asr-ready",
    asr: {
      method: metadata.transcription_method,
      backend: metadata.asr_backend,
      model: metadata.asr_model,
      networkPolicy: metadata.asr_network_policy,
      normalization: metadata.transcript_normalization,
      audioPath: audioFile,
    },
  });
  prepared.resolved_url = metadata.webpage_url || options.url;
  prepared.extracted_at = metadata.extracted_at || new Date().toISOString();
  writeFileSync(manifestPath, `${JSON.stringify(prepared, null, 2)}\n`);
  return prepared;
}

export function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  if (!isSupportedPublicVideoUrl(options.url)) {
    throw new Error("只接受單一公開 YouTube、youtu.be 或可解析影片的 t.co/X URL；不接受播放清單、頻道或帶 credentials 的 URL。");
  }
  const outDir = path.resolve(options.outDir);
  mkdirSync(outDir, { recursive: true });
  const extractor = path.join(SCRIPT_DIR, "extract_transcript.mjs");
  const extracted = run(process.execPath, [extractor, options.url, "--out-dir", outDir]);
  const manifestPath = findManifest(outDir);
  if (extracted.status === 0) {
    if (!manifestPath) throw new Error("字幕抽取成功但找不到 source manifest。");
    const prepared = prepareWithCaptions(options, manifestPath);
    writeFileSync(manifestPath, `${JSON.stringify(prepared, null, 2)}\n`);
    console.log(JSON.stringify({ ...prepared, source_manifest: manifestPath }, null, 2));
    return prepared;
  }
  if (!manifestPath) failProcess(extracted, "來源準備失敗且沒有留下 manifest。");
  const manifest = readJson(manifestPath);
  if (manifest.capture_status !== "captions-unavailable") failProcess(extracted, "字幕抽取失敗，且不是可進入 ASR fallback 的 captions-unavailable 狀態。");
  if (options.asr === "none") throw new Error("無字幕且未配置 ASR backend；停止，不用 metadata 硬寫報告。");
  const prepared = prepareWithLocalQwen(options, manifestPath);
  console.log(JSON.stringify({ ...prepared, source_manifest: manifestPath }, null, 2));
  return prepared;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
