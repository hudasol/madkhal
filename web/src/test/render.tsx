import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AppRoutes } from "../App";
import { SettingsProvider } from "../settings";
import { route } from "./fixtures";

export function mockFetch(failing: string[] = []) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (failing.some((f) => url.includes(f))) {
      return new Response(
        JSON.stringify({ type: "about:blank", title: "Not found", status: 404, detail: "missing" }),
        {
          status: 404,
          headers: { "content-type": "application/problem+json" },
        },
      );
    }
    const body = route(url);
    if (body === null) return new Response("{}", { status: 404 });
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SettingsProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
        </MemoryRouter>
      </SettingsProvider>
    </QueryClientProvider>,
  );
}
