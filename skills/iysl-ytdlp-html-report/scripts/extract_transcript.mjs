#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TRADITIONAL_CHINESE = ["zh-TW", "zh-Hant", "zh-HK", "zh-MO"];
const SIMPLIFIED_CHINESE = ["zh-Hans", "zh-CN", "zh-SG"];
const FALLBACK_LANGUAGE_GROUPS = [
  { name: "traditional-chinese", patterns: TRADITIONAL_CHINESE },
  { name: "simplified-chinese", patterns: SIMPLIFIED_CHINESE },
  { name: "generic-chinese", patterns: ["zh.*"] },
  { name: "english", patterns: ["en-orig", "en.*"] },
];

export class CaptionsUnavailableError extends Error {
  constructor(message, sourceReceipt, cause = null) {
    super(message);
    this.name = "CaptionsUnavailableError";
    this.sourceReceipt = sourceReceipt;
    if (cause) this.cause = cause;
  }
}

export function usage(exitCode = 2) {
  console.error("用法：extract_transcript.mjs <url> [--out-dir <輸出資料夾>] [--langs <yt-dlp 字幕語言>]");
  process.exit(exitCode);
}

export function parseArgs(args) {
  if (!args[0] || args[0].startsWith("-")) usage();

  const options = { url: args[0], outDir: "ytdlp-html-report-output", langs: null };
  for (let index = 1; index < args.length; index += 1) {
    if (args[index] === "--out-dir") options.outDir = args[++index] || usage();
    else if (args[index] === "--langs") options.langs = args[++index] || usage();
    else usage();
  }
  return options;
}

export function run(command, commandArgs, opts = {}) {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    maxBuffer: 128 * 1024 * 1024,
    ...opts,
  });
  if (result.status !== 0) {
    const err = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
    throw new Error(`${command} 執行失敗（${result.status}）：${err}`);
  }
  return result.stdout;
}

export function normalizeLanguageCode(value) {
  return String(value || "").trim().replace(/_/g, "-").toLowerCase();
}

function hasSubtitleFormats(value) {
  if (Array.isArray(value)) return value.length > 0;
  return Boolean(value && typeof value === "object" && Object.keys(value).length);
}

function languageKeys(value) {
  return Object.entries(value || {})
    .filter(([, formats]) => hasSubtitleFormats(formats))
    .map(([language]) => language);
}

export function buildSubtitleCatalog(metadata) {
  return {
    manual: languageKeys(metadata.subtitles),
    automatic: languageKeys(metadata.automatic_captions),
  };
}

export function sourceLanguageFromMetadata(metadata) {
  const value = metadata.language
    || metadata.original_language
    || metadata.original_language_code
    || metadata.language_code;
  return value ? String(value).trim() : null;
}

export function languageMatches(language, selector) {
  const code = normalizeLanguageCode(language);
  const pattern = normalizeLanguageCode(selector);
  if (!code || !pattern) return false;
  if (pattern === "en-orig") return code === "en" || code === "en-orig";
  if (pattern.endsWith(".*")) {
    const prefix = pattern.slice(0, -2);
    return code === prefix || code.startsWith(`${prefix}-`) || code.startsWith(`${prefix}.`);
  }
  if (pattern.endsWith("*")) return code.startsWith(pattern.slice(0, -1));
  return code === pattern;
}

function languageFamily(language) {
  const code = normalizeLanguageCode(language);
  if (TRADITIONAL_CHINESE.some((pattern) => languageMatches(code, pattern))) return "zh-hant";
  if (SIMPLIFIED_CHINESE.some((pattern) => languageMatches(code, pattern))) return "zh-hans";
  return code.split(/[-.]/)[0];
}

function sameLanguageFamily(left, right) {
  return Boolean(left && right && languageFamily(left) === languageFamily(right));
}

function sourceLanguagePatterns(sourceLanguage) {
  const normalized = normalizeLanguageCode(sourceLanguage);
  if (!normalized) return [];
  if (TRADITIONAL_CHINESE.some((pattern) => languageMatches(normalized, pattern))) {
    return [sourceLanguage, ...TRADITIONAL_CHINESE];
  }
  if (SIMPLIFIED_CHINESE.some((pattern) => languageMatches(normalized, pattern))) {
    return [sourceLanguage, ...SIMPLIFIED_CHINESE];
  }
  const base = normalized.split(/[-.]/)[0];
  return base && base !== normalized ? [sourceLanguage, base] : [sourceLanguage];
}

function splitLanguageSelectors(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function findCandidate(catalog, patterns, reason, sourceLanguage, fallbackOverride = null, order = "kind-first") {
  const attempts = order === "selector-first"
    ? patterns.flatMap((pattern) => ["manual", "automatic"].map((kind) => ({ kind, pattern })))
    : ["manual", "automatic"].flatMap((kind) => patterns.map((pattern) => ({ kind, pattern })));
  for (const { kind, pattern } of attempts) {
      const language = catalog[kind].find((available) => languageMatches(available, pattern));
      if (!language) continue;
      return {
        language,
        kind,
        isFallbackLanguage: typeof fallbackOverride === "function"
          ? fallbackOverride(language)
          : (fallbackOverride ?? !sameLanguageFamily(language, sourceLanguage)),
        reason,
      };
  }
  return null;
}

export function selectSubtitleCandidate(metadata, { langsOverride = null } = {}) {
  const sourceLanguage = sourceLanguageFromMetadata(metadata);
  const catalog = buildSubtitleCatalog(metadata);
  const requested = splitLanguageSelectors(langsOverride);

  if (requested.length) {
    return findCandidate(catalog, requested, "user-override", sourceLanguage, sourceLanguage
      ? (language) => !sameLanguageFamily(language, sourceLanguage)
      : true, "selector-first");
  }

  if (sourceLanguage) {
    const original = findCandidate(catalog, sourceLanguagePatterns(sourceLanguage), "original-language", sourceLanguage, false);
    if (original) return original;
  }

  for (const group of FALLBACK_LANGUAGE_GROUPS) {
    const fallback = findCandidate(catalog, group.patterns, `fallback-${group.name}`, sourceLanguage, true);
    if (fallback) return fallback;
  }
  return null;
}

function selectionRecord(selection, sourceLanguage, catalog, requestedLanguages) {
  return {
    source_language: sourceLanguage,
    requested_languages: requestedLanguages || null,
    available_manual: catalog.manual,
    available_automatic: catalog.automatic,
    selected_language: selection?.language || null,
    selected_kind: selection?.kind || null,
    is_fallback_language: selection?.isFallbackLanguage ?? false,
    selection_reason: selection?.reason || (requestedLanguages ? "user-override-no-match" : "no-subtitle-available"),
  };
}

function subtitleMetadataFields({ sourceLanguage, catalog, selection, requestedLanguages }) {
  const record = selectionRecord(selection, sourceLanguage, catalog, requestedLanguages);
  return {
    source_language: sourceLanguage,
    available_subtitles: catalog,
    subtitle_language: record.selected_language,
    subtitle_kind: record.selected_kind,
    subtitle_is_fallback: record.is_fallback_language,
    subtitle_selection: record,
  };
}

function safeSlug(value) {
  return String(value || "video")
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 80)
    .toLowerCase() || "video";
}

function timestamp(ms) {
  const total = Math.floor((ms || 0) / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function decodeEntities(text) {
  return text
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function cleanJson3(file) {
  const json = JSON.parse(readFileSync(file, "utf8"));
  const lines = [];
  for (const event of json.events || []) {
    if (!event.segs) continue;
    const text = event.segs.map((seg) => seg.utf8 || "").join("").replace(/\s+/g, " ").trim();
    if (!text) continue;
    lines.push({ timeMs: event.tStartMs || 0, text: decodeEntities(text.replace(/^>>\s*/, "")) });
  }
  return chunkLines(lines);
}

function cleanVtt(file) {
  const raw = readFileSync(file, "utf8").split(/\r?\n/);
  const lines = [];
  let currentTime = 0;
  for (const line of raw) {
    if (!line.trim() || line.startsWith("WEBVTT") || line.startsWith("Kind:") || line.startsWith("Language:")) continue;
    const timing = line.match(/^(\d\d):(\d\d):(\d\d)\.(\d+)\s+-->/);
    if (timing) {
      currentTime = Number(timing[1]) * 3600000 + Number(timing[2]) * 60000 + Number(timing[3]) * 1000 + Number(timing[4].slice(0, 3));
      continue;
    }
    const text = decodeEntities(line.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim().replace(/^>>\s*/, ""));
    if (text) lines.push({ timeMs: currentTime, text });
  }
  return chunkLines(lines);
}

function chunkLines(lines) {
  const chunks = [];
  let current = [];
  let start = 0;
  let last = "";

  for (const line of lines) {
    if (!line.text || line.text === last) continue;
    if (!current.length) start = line.timeMs;
    current.push(line.text);
    last = line.text;
    const joined = current.join(" ");
    if (joined.length > 900 || (/[.!?。！？]$/.test(line.text) && joined.length > 420)) {
      chunks.push({ time: timestamp(start), timeMs: start, text: joined.replace(/\s+/g, " ") });
      current = [];
    }
  }
  if (current.length) {
    chunks.push({ time: timestamp(start), timeMs: start, text: current.join(" ").replace(/\s+/g, " ") });
  }
  return chunks;
}

function subtitleFileForCandidate(transcriptDir, id, candidate) {
  if (!candidate) return null;
  const prefix = `${id}.${candidate.language}.`;
  const files = readdirSync(transcriptDir)
    .filter((file) => file.startsWith(prefix) && /\.(json3|vtt)$/i.test(file))
    .map((file) => path.join(transcriptDir, file));
  return files.find((file) => file.endsWith(".json3")) || files.find((file) => file.endsWith(".vtt")) || null;
}

function baseMetadata(metadataFull, id, url, selection, catalog, requestedLanguages) {
  const sourceLanguage = sourceLanguageFromMetadata(metadataFull);
  return {
    id,
    title: metadataFull.title || metadataFull.fulltitle || id,
    channel: metadataFull.channel || metadataFull.uploader || "",
    uploader: metadataFull.uploader || "",
    webpage_url: metadataFull.webpage_url || `https://www.youtube.com/watch?v=${id}`,
    requested_url: url,
    original_url: metadataFull.original_url || url,
    duration: metadataFull.duration || null,
    duration_string: metadataFull.duration_string || "",
    upload_date: metadataFull.upload_date || "",
    thumbnail: metadataFull.thumbnail || `https://i.ytimg.com/vi/${id}/maxresdefault.jpg`,
    language: sourceLanguage,
    original_language: metadataFull.original_language || sourceLanguage,
    extracted_at: new Date().toISOString(),
    ...subtitleMetadataFields({ sourceLanguage, catalog, selection, requestedLanguages }),
  };
}

function writeUnavailableArtifacts({ metadataPath, manifestPath, base, id, slug, url, reason }) {
  const metadata = {
    ...base,
    subtitle_file: null,
    subtitle_format: null,
    subtitle_status: "unavailable",
    subtitle_unavailable_reason: reason,
  };
  writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
  const manifest = {
    id,
    slug,
    url,
    metadata: metadataPath,
    transcript: null,
    subtitle: null,
    chunks: 0,
    capture_status: "captions-unavailable",
    subtitle_status: "unavailable",
    ...subtitleMetadataFields({
      sourceLanguage: base.source_language,
      catalog: base.available_subtitles,
      selection: base.subtitle_selection.selected_language ? {
        language: base.subtitle_selection.selected_language,
        kind: base.subtitle_selection.selected_kind,
        isFallbackLanguage: base.subtitle_selection.is_fallback_language,
        reason: base.subtitle_selection.selection_reason,
      } : null,
      requestedLanguages: base.subtitle_selection.requested_languages,
    }),
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  return {
    id,
    slug,
    title: metadata.title,
    url,
    source_language: metadata.source_language,
    subtitle_language: metadata.subtitle_language,
    subtitle_kind: metadata.subtitle_kind,
    subtitle_is_fallback: metadata.subtitle_is_fallback,
    metadata: metadataPath,
    manifest: manifestPath,
    transcript: null,
    subtitle: null,
    chunks: 0,
    capture_status: "captions-unavailable",
  };
}

function subtitleDownloadArgs({ transcriptDir, id, url, candidate }) {
  const kindFlag = candidate.kind === "manual" ? "--write-subs" : "--write-auto-subs";
  return [
    "--no-playlist",
    "--skip-download",
    kindFlag,
    "--sub-langs",
    candidate.language,
    "--sub-format",
    "json3/vtt",
    "--output",
    path.join(transcriptDir, "%(id)s.%(ext)s"),
    url,
  ];
}

export function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  const outDir = path.resolve(options.outDir);
  mkdirSync(outDir, { recursive: true });
  const transcriptDir = path.join(outDir, "transcripts");
  mkdirSync(transcriptDir, { recursive: true });

  const metadataRaw = run("yt-dlp", ["--dump-json", "--skip-download", "--no-warnings", "--no-playlist", options.url]);
  const metadataFull = JSON.parse(metadataRaw);
  if (metadataFull._type === "playlist" || Array.isArray(metadataFull.entries)) {
    throw new Error("這個 skill 不支援播放清單或頻道 URL。請提供單一公開影片 URL。");
  }
  const id = metadataFull.id || metadataFull.display_id;
  if (!id) throw new Error("yt-dlp 回傳的 metadata 沒有影片 id");

  const slug = `${safeSlug(metadataFull.title || metadataFull.fulltitle || id)}-${id}`;
  const metadataPath = path.join(outDir, `${id}.metadata.json`);
  const manifestPath = path.join(outDir, `${id}.manifest.json`);
  const sourceLanguage = sourceLanguageFromMetadata(metadataFull);
  const catalog = buildSubtitleCatalog(metadataFull);
  const selection = selectSubtitleCandidate(metadataFull, { langsOverride: options.langs });
  const base = baseMetadata(metadataFull, id, options.url, selection, catalog, options.langs);

  if (!selection) {
    const reason = options.langs
      ? `沒有符合使用者指定 --langs ${options.langs} 的字幕`
      : "metadata 沒有可用的人工或自動字幕";
    const sourceReceipt = writeUnavailableArtifacts({ metadataPath, manifestPath, base, id, slug, url: options.url, reason });
    throw new CaptionsUnavailableError(`找不到 ${id} 的字幕檔。${reason}。`, sourceReceipt);
  }

  try {
    run("yt-dlp", subtitleDownloadArgs({ transcriptDir, id, url: options.url, candidate: selection }));
  } catch (error) {
    const sourceReceipt = writeUnavailableArtifacts({
      metadataPath,
      manifestPath,
      base,
      id,
      slug,
      url: options.url,
      reason: `選定字幕下載失敗：${error.message}`,
    });
    throw new CaptionsUnavailableError(error.message, sourceReceipt, error);
  }

  const subtitleFile = subtitleFileForCandidate(transcriptDir, id, selection);
  if (!subtitleFile || !existsSync(subtitleFile)) {
    const sourceReceipt = writeUnavailableArtifacts({
      metadataPath,
      manifestPath,
      base,
      id,
      slug,
      url: options.url,
      reason: `metadata 選定 ${selection.language} (${selection.kind})，但 yt-dlp 沒有寫出對應字幕檔`,
    });
    throw new CaptionsUnavailableError(
      `找不到 metadata 選定的 ${selection.language} (${selection.kind}) 字幕檔。`,
      sourceReceipt,
    );
  }

  const chunks = subtitleFile.endsWith(".json3") ? cleanJson3(subtitleFile) : cleanVtt(subtitleFile);
  if (!chunks.length) throw new Error(`字幕檔可以解析，但沒有取得文字內容：${subtitleFile}`);

  const metadata = {
    ...base,
    subtitle_file: subtitleFile,
    subtitle_format: path.extname(subtitleFile).slice(1),
    subtitle_status: "available",
  };
  const transcriptPath = path.join(transcriptDir, `${id}.clean-transcript.md`);
  const transcript = [
    "# 整理後逐字稿",
    "",
    `來源：${metadata.webpage_url}`,
    `原始 URL：${metadata.original_url}`,
    `標題：${metadata.title}`,
    `頻道：${metadata.channel}`,
    `原始語言：${metadata.source_language || "未知"}`,
    `字幕：${metadata.subtitle_language}（${metadata.subtitle_kind}）`,
    `字幕檔：${path.relative(outDir, subtitleFile)}`,
    "備註：由 yt-dlp 依 metadata 字幕選擇結果抽取。",
    "",
    ...chunks.map((chunk) => `## ${chunk.time}\n\n${chunk.text}\n`),
  ].join("\n");

  writeFileSync(transcriptPath, transcript);
  writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
  const manifest = {
    id,
    slug,
    url: options.url,
    metadata: metadataPath,
    transcript: transcriptPath,
    subtitle: subtitleFile,
    chunks: chunks.length,
    capture_status: "captions-ready",
    subtitle_status: "available",
    ...subtitleMetadataFields({ sourceLanguage, catalog, selection, requestedLanguages: options.langs }),
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

  return {
    id,
    slug,
    title: metadata.title,
    url: options.url,
    source_language: metadata.source_language,
    subtitle_language: metadata.subtitle_language,
    subtitle_kind: metadata.subtitle_kind,
    subtitle_is_fallback: metadata.subtitle_is_fallback,
    metadata: metadataPath,
    manifest: manifestPath,
    transcript: transcriptPath,
    subtitle: subtitleFile,
    chunks: chunks.length,
    capture_status: "captions-ready",
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(JSON.stringify(main(), null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
