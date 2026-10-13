// @vitest-environment node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC = dirname(fileURLToPath(import.meta.url));
const URL_RE = /https?:\/\/[^\s"'`)]+/g;
const ALLOWED = [/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/];

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return files(p);
    return /\.(ts|tsx|css)$/.test(name) && !name.endsWith(".test.ts") ? [p] : [];
  });
}

describe("network policy", () => {
  it("MK-L8-009 source makes no call to any external host (no tiles, CDN fonts or analytics)", () => {
    const offenders: string[] = [];
    for (const f of files(SRC)) {
      for (const m of readFileSync(f, "utf-8").match(URL_RE) ?? []) {
        if (!ALLOWED.some((re) => re.test(m))) offenders.push(`${f}: ${m}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it("MK-L8-009 fonts are self hosted through @fontsource and the page loads nothing else", () => {
    const main = readFileSync(join(SRC, "main.tsx"), "utf-8");
    expect(main).toMatch(/@fontsource\/space-grotesk/);
    expect(main).toMatch(/@fontsource\/ibm-plex-sans-arabic/);
    const html = readFileSync(join(SRC, "..", "index.html"), "utf-8");
    expect(html).not.toMatch(URL_RE);
    const pkg = JSON.parse(readFileSync(join(SRC, "..", "package.json"), "utf-8")) as {
      dependencies: Record<string, string>;
    };
    for (const dep of Object.keys(pkg.dependencies)) {
      expect(dep).not.toMatch(/analytics|gtag|sentry|segment|mixpanel|hotjar/i);
    }
  });
});
