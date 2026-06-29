#!/usr/bin/env node
/**
 * OpenAPI → TypeScript 生成占位脚本。
 * M4 阶段手写 client；后续可接入 openapi-typescript。
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const baseline = resolve(__dirname, "../../../tests/fixtures/openapi_baseline.json");

if (!existsSync(baseline)) {
  console.warn("[api-types] OpenAPI baseline not found:", baseline);
  console.warn("[api-types] Skipping generation (stub only).");
  process.exit(0);
}

const spec = JSON.parse(readFileSync(baseline, "utf8"));
const pathCount = Object.keys(spec.paths ?? {}).length;
console.log(`[api-types] OpenAPI baseline: ${pathCount} paths (generation not yet wired).`);
console.log("[api-types] Use createApiClient() from @infinite-canvas/api-types/client for now.");
