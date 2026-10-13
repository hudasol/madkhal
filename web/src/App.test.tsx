import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NAV } from "./App";
import { mockFetch, renderAt } from "./test/render";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("banner", () => {
  it.each(NAV.map((n) => n.path))(
    "MK-L8-002 banner is on screen %s and cannot be dismissed",
    async (path) => {
      mockFetch();
      renderAt(path);
      const banner = await screen.findByTestId("banner");
      expect(banner).toHaveTextContent(
        "Evidence: real satellite history from the Nadhir hindcast.",
      );
      expect(banner).toHaveTextContent(
        "Plant, drone and consequences: hypothetical, synthetic parameters.",
      );
      expect(within(banner).queryAllByRole("button")).toHaveLength(0);
    },
  );
});

describe("console", () => {
  it("MK-L8-001 renders one tile per site with intervals", async () => {
    mockFetch();
    renderAt("/");
    expect(await screen.findByTestId("tile-kalba")).toBeInTheDocument();
    expect(await screen.findByTestId("tile-alraha")).toBeInTheDocument();
    const tile = screen.getByTestId("tile-kalba");
    expect(within(tile).getAllByRole("img").length).toBeGreaterThanOrEqual(4);
    expect(within(tile).getByText(/Coordinates ESTIMATED/)).toBeInTheDocument();
  });

  it("MK-L8-001 shows an error state with retry when the API fails", async () => {
    mockFetch(["/v1/sites"]);
    renderAt("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("evidence", () => {
  it("MK-L8-001 shows the track record with counts beside the rate", async () => {
    mockFetch();
    renderAt("/evidence");
    expect(await screen.findByText(/caught 1 of 3 observable/)).toBeInTheDocument();
    expect(screen.getByText(/19 of 426/)).toBeInTheDocument();
    expect(screen.getAllByText("UNVERIFIED").length).toBeGreaterThan(0);
  });
});
