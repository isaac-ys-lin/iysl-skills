import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { readAndValidateReportV2, readingMinutes as readingMinutesV23 } from "./validate_report_v2.mjs";
import { readAndValidateReportV24, readingMinutes as readingMinutesV24, reportWarnings } from "./validate_report_v2_4.mjs";

export function readAndValidateReport(inputPath, options = {}) {
  const version = JSON.parse(readFileSync(inputPath, "utf8")).version;
  if (version === "2.4") return readAndValidateReportV24(inputPath, options);
  // v2.3 validator remains the compatibility authority, including its historical
  // error text for missing or unsupported legacy versions.
  return readAndValidateReportV2(inputPath, options);
}

function usage() {
  console.error("用法：validate_report.mjs <report.json> [--transcript <clean-transcript.md>] [--print-reading-minutes]");
  process.exit(2);
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const inputPath = process.argv[2] || usage();
  try {
    const raw = JSON.parse(readFileSync(inputPath, "utf8"));
    if (process.argv.includes("--print-reading-minutes")) {
      const calculator = raw.version === "2.4" ? readingMinutesV24 : readingMinutesV23;
      console.log(String(calculator(raw)));
      process.exit(0);
    }
    const transcriptIndex = process.argv.indexOf("--transcript");
    const transcriptPath = transcriptIndex >= 0 ? process.argv[transcriptIndex + 1] : "";
    if (transcriptIndex >= 0 && !transcriptPath) usage();
    const spec = readAndValidateReport(inputPath, {
      transcript: transcriptPath ? readFileSync(transcriptPath, "utf8") : "",
    });
    console.log(JSON.stringify({
      valid: true,
      version: spec.version,
      blocks: spec.blocks.length,
      topics: spec.topic_coverage.topics.length,
      ...(spec.semantic_inventory ? { semantic_units: spec.semantic_inventory.length } : {}),
      ...(spec.interpretations ? { interpretations: spec.interpretations.length } : {}),
      ...(spec.version === "2.4" ? { warnings: reportWarnings(spec) } : {}),
    }, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
