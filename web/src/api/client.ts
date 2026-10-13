// Data access. Live mode calls the product's own API under /v1 (proxied by Vite in
// development). Static mode reads the JSON files written by `madkhal snapshot`; query
// parameters are not available there, so screens use the precomputed defaults.
// No other network call is made by the web app.

declare const __MADKHAL_MODE__: "live" | "static";

export type Mode = "live" | "static";

export const MODE: Mode = typeof __MADKHAL_MODE__ !== "undefined" ? __MADKHAL_MODE__ : "live";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly title: string,
    public readonly detail: string,
  ) {
    super(`${status} ${title}: ${detail}`);
  }
}

export type Query = Record<string, string | number | undefined>;

export function liveUrl(route: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined) params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${route}?${qs}` : route;
}

export function staticUrl(route: string, base: string = import.meta.env.BASE_URL): string {
  const b = base.endsWith("/") ? base : `${base}/`;
  return `${b}api${route}.json`;
}

export async function getJson<T>(route: string, query?: Query, mode: Mode = MODE): Promise<T> {
  const url = mode === "static" ? staticUrl(route) : liveUrl(route, query);
  const res = await fetch(url, { headers: { accept: "application/json" } });
  if (!res.ok) {
    let title = res.statusText || "Error";
    let detail = "";
    try {
      const body = (await res.json()) as { title?: string; detail?: string };
      title = body.title ?? title;
      detail = body.detail ?? "";
    } catch {
      // not a problem+json body
    }
    throw new ApiError(res.status, title, detail);
  }
  return (await res.json()) as T;
}
