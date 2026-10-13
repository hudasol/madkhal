// @vitest-environment node
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// WCAG 2.2 contrast checks on the design tokens in theme.css, for both themes.
const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "theme.css"), "utf-8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`missing ${selector}`);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  const out: Record<string, string> = {};
  for (const m of css.slice(open + 1, close).matchAll(/(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    out[m[1]!] = m[2]!;
  }
  return out;
}

function lum(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const lin = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * lin[0]! + 0.7152 * lin[1]! + 0.0722 * lin[2]!;
}

export function contrast(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x! + 0.05) / (y! + 0.05);
}

const light = block(":root {");
const dark = { ...light, ...block(':root[data-theme="dark"]') };
const TEXT = ["--text", "--ink", "--text-muted", "--link"];
const GRAPHIC = [
  "--border",
  "--line",
  "--go",
  "--derate",
  "--park",
  "--nosafe",
  "--inspect",
  "--alert-cell",
  "--nodata",
  "--focus",
];
const BACKGROUNDS = ["--bg", "--surface", "--surface-2"];

describe("contrast", () => {
  for (const [name, theme] of [
    ["light", light],
    ["dark", dark],
  ] as const) {
    it(`MK-L8-005 text tokens meet AA (4.5:1) on every background, ${name} theme`, () => {
      for (const fg of TEXT) {
        for (const bg of BACKGROUNDS) {
          const r = contrast(theme[fg]!, theme[bg]!);
          expect(r, `${fg} on ${bg} = ${r.toFixed(2)}`).toBeGreaterThanOrEqual(4.5);
        }
      }
    });

    it(`MK-L8-005 graphical tokens meet 3:1 on every background, ${name} theme`, () => {
      for (const fg of GRAPHIC) {
        for (const bg of BACKGROUNDS) {
          const r = contrast(theme[fg]!, theme[bg]!);
          expect(r, `${fg} on ${bg} = ${r.toFixed(2)}`).toBeGreaterThanOrEqual(3);
        }
      }
    });
  }

  it("MK-L8-005 the brand pastels are kept away from text roles", () => {
    expect(contrast(light["--accent"]!, light["--bg"]!)).toBeLessThan(4.5); // why darker tones exist
    expect(TEXT.map((k) => light[k])).not.toContain(light["--accent"]);
  });
});
