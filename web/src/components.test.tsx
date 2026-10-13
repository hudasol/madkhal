import { fireEvent, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NAV } from "./App";
import { ActionGlyph, type ActionCode } from "./components/ActionBadge";
import { BandChart } from "./components/BandChart";
import { DotWhisker } from "./components/DotWhisker";
import { Ribbon } from "./components/Ribbon";
import { formatInstant, formatNumber } from "./format";
import { SettingsProvider } from "./settings";
import { mockFetch, renderAt } from "./test/render";

vi.mock("maplibre-gl", () => ({ default: {} }));

afterEach(() => vi.unstubAllGlobals());

const HERE = dirname(fileURLToPath(import.meta.url));

describe("screens", () => {
  it.each(NAV.map((n) => [n.path, n.key]))(
    "MK-L8-003 route %s renders its screen with a heading",
    async (path) => {
      mockFetch();
      renderAt(path);
      expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
      expect(screen.getByTestId("banner")).toBeInTheDocument();
    },
  );

  it("MK-L8-012 screens show an error state with retry when data is missing", async () => {
    mockFetch(["/v1/policies/results"]);
    renderAt("/policies");
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load");
  });

  it("MK-L8-012 loading state is announced", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => undefined)),
    );
    renderAt("/plant");
    expect(screen.getAllByRole("status")[0]).toHaveAttribute("aria-busy", "true");
  });

  it("MK-L8-011 the shift handover has a print control and a print stylesheet", async () => {
    mockFetch();
    renderAt("/handover");
    expect(await screen.findByRole("button", { name: "Print" })).toBeInTheDocument();
    const css = readFileSync(join(HERE, "theme.css"), "utf-8");
    expect(css).toMatch(/@media print/);
  });
});

describe("encoding", () => {
  it("MK-L8-006 every action has its own shape, not only a colour", () => {
    const codes: ActionCode[] = ["GO", "DERATE", "PARK", "NO_SAFE_OPTION_ESCALATE", "INSPECT"];
    const signatures = codes.map((c) => {
      const { container, unmount } = render(<ActionGlyph action={c} />);
      const sig = Array.from(container.querySelectorAll("svg *"))
        .filter(
          (e) =>
            !["defs", "pattern", "line"].includes(e.tagName) ||
            e.parentElement?.tagName !== "pattern",
        )
        .map(
          (e) =>
            `${e.tagName}:${e.getAttribute("points") ?? e.getAttribute("d") ?? e.getAttribute("r") ?? ""}`,
        )
        .join("|");
      unmount();
      return sig;
    });
    expect(new Set(signatures).size).toBe(codes.length);
    const { container } = render(<ActionGlyph action="DERATE" />);
    expect(container.querySelector("pattern")).not.toBeNull();
  });
});

describe("charts", () => {
  const dates = ["2020-01-01", "2020-01-02"];
  const band = { lo: [0.1, 0.2], median: [0.2, 0.3], hi: [0.4, 0.5] };
  it.each([
    [
      "band",
      <BandChart
        key="b"
        title="Band"
        description="desc"
        dates={dates}
        band={band}
        clear={[true, false]}
        alert={[false, false]}
      />,
    ],
    [
      "ribbon",
      <Ribbon
        key="r"
        title="Ribbon"
        description="desc"
        dates={dates}
        actions={["GO", "DERATE"]}
        scales={[1, 0.7]}
      />,
    ],
    [
      "dots",
      <DotWhisker
        key="d"
        title="Dots"
        description="desc"
        unit="CU"
        rows={[{ label: "a", mean: 1, lo: 0, hi: 2 }]}
      />,
    ],
  ])("MK-L8-007 %s chart has a label, intervals and a table alternative", (_name, el) => {
    render(<SettingsProvider>{el}</SettingsProvider>);
    const img = screen.getAllByRole("img")[0]!;
    expect(img.getAttribute("aria-label")).toMatch(/desc/);
    fireEvent.click(screen.getByRole("button", { name: "Show table" }));
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row").length).toBeGreaterThan(1);
  });
});

describe("language and time", () => {
  it("MK-L8-004 Arabic Indic digits on request, and right to left in Arabic", async () => {
    expect(formatNumber(2023, { lang: "ar", arabicDigits: true })).toMatch(/[٠-٩]/);
    expect(formatNumber(2023, { lang: "ar", arabicDigits: false })).not.toMatch(/[٠-٩]/);
    mockFetch();
    renderAt("/");
    fireEvent.click(await screen.findByRole("button", { name: "Switch to Arabic" }));
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    fireEvent.click(await screen.findByRole("button", { name: "التبديل إلى الإنجليزية" }));
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("MK-L8-013 instants show in Asia/Dubai with UTC for the tooltip", () => {
    const f = formatInstant("2020-01-01T02:00:00Z", { lang: "en", arabicDigits: false });
    expect(f.local).toMatch(/6:00/);
    expect(f.utc).toBe("2020-01-01 02:00 UTC");
  });

  it("MK-L8-004 every Arabic message key exists for every English key", async () => {
    const en = (await import("./i18n/en")).default;
    const ar = (await import("./i18n/ar")).default;
    const enS = (await import("./i18n/enScreens")).default;
    const arS = (await import("./i18n/arScreens")).default;
    const keys = (o: object, p = ""): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        typeof v === "object" && v ? keys(v as object, `${p}${k}.`) : [`${p}${k}`],
      );
    expect(keys(ar).sort()).toEqual(keys(en).sort());
    expect(keys(arS).sort()).toEqual(keys(enS).sort());
  });
});
