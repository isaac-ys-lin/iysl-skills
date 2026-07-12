#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);

function usage() {
  console.error("用法：extract_transcript.mjs <url> [--out-dir <輸出資料夾>] [--langs <yt-dlp 字幕語言>]");
  process.exit(2);
}

if (!args[0] || args[0].startsWith("-")) usage();

const url = args[0];
let outDir = "ytdlp-html-report-output";
let langs = "en-orig,en.*";

for (let i = 1; i < args.length; i += 1) {
  if (args[i] === "--out-dir") {
    outDir = args[++i] || usage();
  } else if (args[i] === "--langs") {
    langs = args[++i] || usage();
  } else {
    usage();
  }
}

function run(command, commandArgs, opts = {}) {
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

function pickSubtitleFile(transcriptDir, id) {
  const files = readdirSync(transcriptDir)
    .filter((file) => file.startsWith(`${id}.`) && /\.(json3|vtt)$/i.test(file))
    .map((file) => path.join(transcriptDir, file));
  const rank = (file) => {
    const base = path.basename(file);
    if (base.endsWith(".en-orig.json3")) return 0;
    if (/\.en[^.]*\.json3$/.test(base)) return 1;
    if (base.endsWith(".json3")) return 2;
    if (base.endsWith(".en-orig.vtt")) return 3;
    if (/\.en[^.]*\.vtt$/.test(base)) return 4;
    return 5;
  };
  return files.sort((a, b) => rank(a) - rank(b))[0];
}

mkdirSync(outDir, { recursive: true });
const transcriptDir = path.join(outDir, "transcripts");
mkdirSync(transcriptDir, { recursive: true });

const metadataRaw = run("yt-dlp", ["--dump-json", "--skip-download", "--no-warnings", "--no-playlist", url]);
const metadataFull = JSON.parse(metadataRaw);
if (metadataFull._type === "playlist" || Array.isArray(metadataFull.entries)) {
  throw new Error("這個 skill 不支援播放清單或頻道 URL。請提供單一公開影片 URL。");
}
const id = metadataFull.id || metadataFull.display_id;
if (!id) throw new Error("yt-dlp 回傳的 metadata 沒有影片 id");

run("yt-dlp", [
  "--no-playlist",
  "--skip-download",
  "--write-auto-subs",
  "--write-subs",
  "--sub-langs",
  langs,
  "--sub-format",
  "json3/vtt",
  "--output",
  path.join(transcriptDir, "%(id)s.%(ext)s"),
  url,
]);

const subtitleFile = pickSubtitleFile(transcriptDir, id);
if (!subtitleFile || !existsSync(subtitleFile)) {
  throw new Error(`找不到 ${id} 的字幕檔。這支影片可能沒有符合 --langs ${langs} 的字幕。`);
}

const chunks = subtitleFile.endsWith(".json3") ? cleanJson3(subtitleFile) : cleanVtt(subtitleFile);
if (!chunks.length) throw new Error(`字幕檔可以解析，但沒有取得文字內容：${subtitleFile}`);

const metadata = {
  id,
  title: metadataFull.title || metadataFull.fulltitle || id,
  channel: metadataFull.channel || metadataFull.uploader || "",
  uploader: metadataFull.uploader || "",
  webpage_url: metadataFull.webpage_url || `https://www.youtube.com/watch?v=${id}`,
  original_url: metadataFull.original_url || url,
  duration: metadataFull.duration || null,
  duration_string: metadataFull.duration_string || "",
  upload_date: metadataFull.upload_date || "",
  thumbnail: metadataFull.thumbnail || `https://i.ytimg.com/vi/${id}/maxresdefault.jpg`,
  subtitle_file: subtitleFile,
  subtitle_format: path.extname(subtitleFile).slice(1),
  extracted_at: new Date().toISOString(),
};

const slug = `${safeSlug(metadata.title)}-${id}`;
const transcriptPath = path.join(transcriptDir, `${id}.clean-transcript.md`);
const metadataPath = path.join(outDir, `${id}.metadata.json`);
const manifestPath = path.join(outDir, `${id}.manifest.json`);

const transcript = [
  "# 整理後逐字稿",
  "",
  `來源：${metadata.webpage_url}`,
  `原始 URL：${metadata.original_url}`,
  `標題：${metadata.title}`,
  `頻道：${metadata.channel}`,
  `字幕：${path.relative(outDir, subtitleFile)}`,
  "備註：由 yt-dlp 從可用字幕抽取。",
  "",
  ...chunks.map((chunk) => `## ${chunk.time}\n\n${chunk.text}\n`),
].join("\n");

writeFileSync(transcriptPath, transcript);
writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
writeFileSync(manifestPath, `${JSON.stringify({
  id,
  slug,
  url,
  metadata: metadataPath,
  transcript: transcriptPath,
  subtitle: subtitleFile,
  chunks: chunks.length,
}, null, 2)}\n`);

console.log(JSON.stringify({
  id,
  slug,
  title: metadata.title,
  metadata: metadataPath,
  transcript: transcriptPath,
  subtitle: subtitleFile,
  chunks: chunks.length,
}, null, 2));
