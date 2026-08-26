#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_PRINT_CSS = path.join(SCRIPT_DIR, "..", "assets", "report-print.css");

function usage(exitCode = 2) {
  console.error("用法：export_report_pdf.mjs --html <report.html> --pdf <report.pdf> [--browser-executable <chrome-or-chromium>] [--print-css <report-print.css>] [--browser-timeout-ms <milliseconds>]");
  process.exit(exitCode);
}

function parseArgs(args) {
  const options = { html: "", pdf: "", browserExecutable: "", printCss: DEFAULT_PRINT_CSS, browserTimeoutMs: 15000 };
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    const value = args[index + 1];
    if (!["--html", "--pdf", "--browser-executable", "--print-css", "--browser-timeout-ms"].includes(key) || !value || value.startsWith("--")) usage();
    if (key === "--html") options.html = value;
    else if (key === "--pdf") options.pdf = value;
    else if (key === "--browser-executable") options.browserExecutable = value;
    else if (key === "--print-css") options.printCss = value;
    else {
      options.browserTimeoutMs = Number.parseInt(value, 10);
      if (!Number.isInteger(options.browserTimeoutMs) || options.browserTimeoutMs < 100) usage();
    }
    index += 1;
  }
  if (!options.html || !options.pdf) usage();
  return options;
}

function browserCandidates(explicit) {
  return [
    explicit,
    process.env.CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
}

function resolveBrowser(explicit) {
  const browser = browserCandidates(explicit).find((candidate) => {
    try {
      return existsSync(candidate) && statSync(candidate).isFile();
    } catch {
      return false;
    }
  });
  if (!browser) {
    throw new Error("PDF export 需要本機 Chrome/Chromium；請用 --browser-executable 指定 executable");
  }
  return browser;
}

function injectPrintContract(html, css, sourceDirectory) {
  if (!/<head\b[^>]*>/i.test(html) || !/<\/head>/i.test(html)) {
    throw new Error("PDF export 需要完整 HTML head");
  }
  if (/<style\b[^>]*data-iysl-report-print=/i.test(html)) {
    throw new Error("HTML 已含 data-iysl-report-print；不要重複注入列印契約");
  }
  if (/<\/style/i.test(css)) throw new Error("print CSS 不可包含 </style");
  const baseHref = pathToFileURL(`${sourceDirectory}${path.sep}`).href;
  const injection = `<base href="${baseHref}"><style data-iysl-report-print="v1">\n${css}\n</style>`;
  return html.replace(/<\/head>/i, `${injection}</head>`);
}

function main(args = process.argv.slice(2)) {
  const options = parseArgs(args);
  const htmlPath = path.resolve(options.html);
  const pdfPath = path.resolve(options.pdf);
  const cssPath = path.resolve(options.printCss);
  if (!existsSync(htmlPath)) throw new Error(`找不到 HTML：${htmlPath}`);
  if (!existsSync(cssPath)) throw new Error(`找不到 print CSS：${cssPath}`);
  const browser = resolveBrowser(options.browserExecutable);
  const html = readFileSync(htmlPath, "utf8");
  const css = readFileSync(cssPath, "utf8");
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "iysl-report-pdf-"));
  const tempHtml = path.join(tempDir, "report.print.html");
  const tempPdf = `${pdfPath}.tmp-${process.pid}-${Date.now()}`;
  mkdirSync(path.dirname(pdfPath), { recursive: true });
  try {
    writeFileSync(tempHtml, injectPrintContract(html, css, path.dirname(htmlPath)), "utf8");
    const profileDir = path.join(tempDir, "chrome-profile");
    const result = spawnSync(browser, [
      "--headless=new",
      "--disable-gpu",
      "--disable-extensions",
      "--disable-background-networking",
      "--disable-sync",
      "--disable-component-update",
      "--no-first-run",
      "--no-default-browser-check",
      "--metrics-recording-only",
      "--no-pdf-header-footer",
      "--print-to-pdf-no-header",
      `--user-data-dir=${profileDir}`,
      `--print-to-pdf=${tempPdf}`,
      pathToFileURL(tempHtml).href,
    ], { stdio: "ignore", timeout: options.browserTimeoutMs, killSignal: "SIGTERM" });
    const validPdfHeader = existsSync(tempPdf)
      && readFileSync(tempPdf).subarray(0, 5).equals(Buffer.from("%PDF-"));
    const timedOutAfterWritingPdf = result.error?.code === "ETIMEDOUT" && validPdfHeader;
    if (result.status !== 0 && !timedOutAfterWritingPdf) {
      const reason = result.error?.code === "ETIMEDOUT"
        ? `超過 ${options.browserTimeoutMs}ms 且沒有完整 PDF header`
        : `exit ${result.status}`;
      throw new Error(`Chrome/Chromium PDF export 失敗（${reason}）`);
    }
    if (!validPdfHeader) {
      throw new Error("Chrome/Chromium 沒有產生有效 PDF header");
    }
    chmodSync(tempPdf, 0o644);
    renameSync(tempPdf, pdfPath);
    console.log(JSON.stringify({
      valid: true,
      report_html: htmlPath,
      report_pdf: pdfPath,
      print_css: cssPath,
      browser_executable: browser,
      browser_completion: timedOutAfterWritingPdf ? "timed_out_after_pdf" : "exited",
    }, null, 2));
  } finally {
    if (existsSync(tempPdf)) rmSync(tempPdf, { force: true });
    rmSync(tempDir, { recursive: true, force: true });
  }
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
