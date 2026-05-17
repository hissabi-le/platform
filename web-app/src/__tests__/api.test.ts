import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchJson } from "@/lib/api";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("fetchJson", () => {
  it("returns parsed JSON on a 200 response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ hello: "world" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    ) as unknown as typeof fetch;

    const result = await fetchJson<{ hello: string }>("/some/path");
    expect(result).toEqual({ hello: "world" });
  });

  it("throws ApiError with the status code on a non-2xx response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "nope" }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      })
    ) as unknown as typeof fetch;

    await expect(fetchJson("/bad")).rejects.toBeInstanceOf(ApiError);
    await expect(fetchJson("/bad")).rejects.toMatchObject({ status: 422 });
  });
});
