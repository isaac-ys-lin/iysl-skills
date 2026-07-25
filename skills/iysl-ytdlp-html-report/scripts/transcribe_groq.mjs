#!/usr/bin/env node
import { homedir } from "node:os";
import { basename, extname, resolve } from "node:path";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";

const args = process.argv.slice(2);

function usage(exitCode = 0) {
  const output = [
    "用法：transcribe_groq.mjs --audio <音訊檔> --out <clean transcript.md> [選項]",
    "",
    "選項：",
    "  --raw-out <response.json>  保留 Groq verbose_json 回應供 operator 查核",
    "  --language <ISO-639-1>     提示音訊語言（預設 en）",
    "  --model <model>            Groq Whisper 模型（預設 whisper-large-v3）",
    "  --config <path>            GROQ_API_KEY 設定檔（預設 $HOME/.a_studio/config）",
  ].join("\n");
  (exitCode === 0 ? console.log : console.error)(output);
  process.exit(exitCode);
}

if (args.includes("--help") || args.includes("-h")) usage();

const options = {
  audio: "",
  out: "",
  rawOut: "",
  language: "en",
  model: "whisper-large-v3",
  config: `${homedir()}/.a_studio/config`,
};

const optionNames = new Map([
  ["--audio", "audio"],
  ["--out", "out"],
  ["--raw-out", "rawOut"],
  ["--language", "language"],
  ["--model", "model"],
  ["--config", "config"],
]);

for (let index = 0; index < args.length; index += 1) {
  const key = optionNames.get(args[index]);
  if (!key) usage(2);
  const value = args[++index];
  if (!value || value.startsWith("--")) usage(2);
  options[key] = value;
}

if (!options.audio || !options.out) usage(2);

function parseGroqApiKey(configPath) {
  if (!existsSync(configPath)) return "";
  const config = readFileSync(configPath, "utf8");
  const match = config.match(/^\s*(?:export\s+)?GROQ_API_KEY\s*=\s*(.*?)\s*$/m);
  if (!match) return "";
  const value = match[1].trim();
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}

function loadGroqApiKey() {
  return process.env.GROQ_API_KEY?.trim() || parseGroqApiKey(options.config);
}

function timestamp(seconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  return hours
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`
    : `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function cleanTranscript(response) {
  const chunks = (response.segments || [])
    .map((segment) => ({
      time: timestamp(segment.start),
      text: String(segment.text || "").replace(/\s+/g, " ").trim(),
    }))
    .filter((segment) => segment.text);

  if (chunks.length) {
    return [
      "# 整理後逐字稿",
      "",
      "備註：由 Groq Whisper 從音訊自動轉錄；時間標記為 ASR segment 起點。",
      "",
      ...chunks.map((segment) => `## ${segment.time}\n\n${segment.text}\n`),
    ].join("\n");
  }

  const text = String(response.text || "").replace(/\s+/g, " ").trim();
  if (!text) throw new Error("Groq 回應沒有可用逐字稿文字。");
  return [
    "# 整理後逐字稿",
    "",
    "備註：由 Groq Whisper 從音訊自動轉錄；服務未回傳可用 segment 時間標記。",
    "",
    text,
    "",
  ].join("\n");
}

const audioPath = resolve(options.audio);
if (!existsSync(audioPath)) throw new Error("找不到指定的音訊檔。");
if (statSync(audioPath).size === 0) throw new Error("指定的音訊檔是空檔。");

const apiKey = loadGroqApiKey();
if (!apiKey) {
  throw new Error("找不到 GROQ_API_KEY；請設定環境變數或在已指定的設定檔提供它。金鑰不會被輸出或寫入 artifact。");
}

const mimeTypes = {
  ".flac": "audio/flac",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
  ".mp4": "audio/mp4",
  ".mpeg": "audio/mpeg",
  ".mpga": "audio/mpeg",
  ".ogg": "audio/ogg",
  ".wav": "audio/wav",
  ".webm": "audio/webm",
};
const mimeType = mimeTypes[extname(audioPath).toLowerCase()] || "application/octet-stream";
const form = new FormData();
form.append("file", new Blob([readFileSync(audioPath)], { type: mimeType }), basename(audioPath));
form.append("model", options.model);
form.append("language", options.language);
form.append("response_format", "verbose_json");
form.append("temperature", "0");
form.append("timestamp_granularities[]", "segment");

const response = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
  method: "POST",
  headers: { Authorization: `Bearer ${apiKey}` },
  body: form,
});
const body = await response.text();
if (!response.ok) {
  throw new Error(`Groq transcription API 回傳 HTTP ${response.status}。請檢查 API 權限、音訊格式與檔案大小。`);
}

let transcription;
try {
  transcription = JSON.parse(body);
} catch {
  throw new Error("Groq transcription API 回傳了無法解析的內容。");
}

const transcript = cleanTranscript(transcription);
writeFileSync(resolve(options.out), transcript, "utf8");
if (options.rawOut) writeFileSync(resolve(options.rawOut), `${JSON.stringify(transcription, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  audio: audioPath,
  transcript: resolve(options.out),
  raw_response: options.rawOut ? resolve(options.rawOut) : null,
  model: options.model,
  language: options.language,
  segments: Array.isArray(transcription.segments) ? transcription.segments.length : 0,
}, null, 2));
