import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getJson, liveUrl, staticUrl } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("client", () => {
  it("MK-L8-010 static mode maps a route to a precomputed JSON file", () => {
    expect(staticUrl("/v1/belief/kalba/series", "./")).toBe("./api/v1/belief/kalba/series.json");
    expect(staticUrl("/v1/sites", "/madkhal")).toBe("/madkhal/api/v1/sites.json");
  });

  it("MK-L8-010 static mode ignores query parameters and fetches the file", async () => {
    const fn = vi.fn(async () => new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fn);
    await getJson("/v1/sites", { dataset: "modis_v1" }, "static");
    expect(String((fn.mock.calls[0] as unknown[])[0])).toMatch(/api\/v1\/sites\.json$/);
  });

  it("MK-L8-009 live mode only calls the product API under /v1", () => {
    expect(liveUrl("/v1/belief/kalba", { date: "2018-09-08", draws: undefined })).toBe(
      "/v1/belief/kalba?date=2018-09-08",
    );
  });

  it("surfaces problem+json details as ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ title: "Invalid input", detail: "bad date" }), {
            status: 422,
          }),
      ),
    );
    await expect(getJson("/v1/belief/kalba", undefined, "live")).rejects.toEqual(
      new ApiError(422, "Invalid input", "bad date"),
    );
  });
});
