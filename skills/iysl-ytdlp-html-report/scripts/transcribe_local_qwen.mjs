#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";

const DEFAULT_MODEL = "Qwen/Qwen3-ASR-1.7B";

function usage(exitCode = 2) {
  console.error([
    "用法：transcribe_local_qwen.mjs --audio <音訊檔> --out <clean transcript.md> [選項]",
    "",
    "選項：",
    `  --model <model>       Qwen3-ASR 模型（預設 ${DEFAULT_MODEL}）`,
    "  --language <name>     強制語言，例如 Chinese 或 English；省略時自動偵測",
    "  --context <terms>     空白分隔的專有名詞提示",
    "  --binary <path>       mlx-qwen3-asr CLI（預設 QWEN3_ASR_BIN 或 PATH）",
    "  --opencc-binary <path> OpenCC CLI（預設 OPENCC_BIN 或 PATH）",
    "  --opencc-config <name> OpenCC 設定（預設 s2twp.json）",
    "  --no-opencc           保留模型原始字形，不轉成台灣繁體",
    "  --allow-model-download 僅首次明確允許下載缺少的模型；預設強制 offline cache",
  ].join("\n"));
  process.exit(exitCode);
}

const options = {
  audio: "",
  out: "",
  model: DEFAULT_MODEL,
  language: "",
  context: "",
  binary: process.env.QWEN3_ASR_BIN?.trim() || "mlx-qwen3-asr",
  openccBinary: process.env.OPENCC_BIN?.trim() || "opencc",
  openccConfig: "s2twp.json",
  noOpencc: false,
  allowModelDownload: false,
};
const optionMap = new Map([
  ["--audio", "audio"],
  ["--out", "out"],
  ["--model", "model"],
  ["--language", "language"],
  ["--context", "context"],
  ["--binary", "binary"],
  ["--opencc-binary", "openccBinary"],
  ["--opencc-config", "openccConfig"],
]);

const args = process.argv.slice(2);
if (args.includes("--help") || args.includes("-h")) usage(0);
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--no-opencc") {
    options.noOpencc = true;
    continue;
  }
  if (args[index] === "--allow-model-download") {
    options.allowModelDownload = true;
    continue;
  }
  const key = optionMap.get(args[index]);
  if (!key || index + 1 >= args.length) usage();
  options[key] = args[++index];
}
if (!options.audio || !options.out || !options.model || !options.binary) usage();
for (const [key, value] of Object.entries(options)) {
  if (typeof value === "string" && value.includes("\0")) throw new Error(`${key} 不可包含 NUL 字元。`);
}

const audioPath = path.resolve(options.audio);
const outputPath = path.resolve(options.out);
if (!existsSync(audioPath)) throw new Error("找不到指定的音訊檔。");
if (!statSync(audioPath).isFile() || statSync(audioPath).size === 0) {
  throw new Error("指定的音訊必須是非空檔案。");
}

const cliArgs = [
  audioPath,
  "--model", options.model,
  "--stdout-only",
  "--no-progress",
];
if (options.language) cliArgs.push("--language", options.language);
if (options.context) cliArgs.push("--context", options.context);

const result = spawnSync(options.binary, cliArgs, {
  encoding: "utf8",
  maxBuffer: 64 * 1024 * 1024,
  env: options.allowModelDownload
    ? process.env
    : { ...process.env, HF_HUB_OFFLINE: "1", TRANSFORMERS_OFFLINE: "1" },
});
if (result.error?.code === "ENOENT") {
  throw new Error("找不到 mlx-qwen3-asr CLI；請先執行 `uv tool install mlx-qwen3-asr`，或用 --binary 指定已安裝的本機 CLI。");
}
if (result.error) throw new Error(`無法啟動本機 Qwen3-ASR：${result.error.message}`);
if (result.status !== 0) {
  const detail = String(result.stderr || result.stdout || "").trim().slice(0, 2000);
  const bootstrapHint = options.allowModelDownload
    ? ""
    : " 若模型尚未快取，僅首次明確加 --allow-model-download。";
  throw new Error(`本機 Qwen3-ASR 失敗（exit ${result.status}）${detail ? `：${detail}` : "。"}${bootstrapHint}`);
}

let transcript = String(result.stdout || "").trim();
if (!transcript) throw new Error("本機 Qwen3-ASR 沒有輸出可用逐字稿。");
if (!options.noOpencc) {
  const converted = spawnSync(options.openccBinary, ["-c", options.openccConfig], {
    input: transcript,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  if (converted.error?.code === "ENOENT") {
    throw new Error("找不到 OpenCC CLI；請先執行 `brew install opencc`，或用 --no-opencc 保留模型原始字形。");
  }
  if (converted.error) throw new Error(`無法啟動 OpenCC：${converted.error.message}`);
  if (converted.status !== 0) {
    const detail = String(converted.stderr || "").trim().slice(0, 2000);
    throw new Error(`OpenCC 轉換失敗（exit ${converted.status}）${detail ? `：${detail}` : "。"}`);
  }
  transcript = String(converted.stdout || "").trim();
  if (!transcript) throw new Error("OpenCC 沒有輸出可用逐字稿。");
}
mkdirSync(path.dirname(outputPath), { recursive: true });
writeFileSync(outputPath, `${transcript}\n`, "utf8");

console.log(JSON.stringify({
  audio: audioPath,
  transcript: outputPath,
  backend: "mlx-qwen3-asr",
  model: options.model,
  language: options.language || "auto",
  context_provided: Boolean(options.context),
  normalization: options.noOpencc ? "none" : `opencc:${options.openccConfig}`,
  model_network_policy: options.allowModelDownload ? "download-allowed" : "offline-cache-only",
}, null, 2));
