// src/app/page.tsx
"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white text-gray-900">
      {/* Top nav */}
      <header className="sticky top-0 z-30 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-black" />
            <span className="font-semibold tracking-tight">Hissabi</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm">
            <a href="#features" className="hover:opacity-70">Features</a>
            <a href="#how-it-works" className="hover:opacity-70">How it works</a>
            <a href="#pricing" className="hover:opacity-70">Pricing</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm underline">Sign in</Link>
            <Link
              href="/login"
              className="rounded-md bg-black px-4 py-2 text-sm text-white hover:opacity-90"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 md:grid-cols-2 md:py-24">
          <div className="space-y-6">
            <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
              Accounting that speaks your language.
            </h1>
            <p className="text-gray-600">
              Upload your business documents (even messy, mixed-language sheets).
              Hissabi cleans, analyzes, and generates balance sheets, P&L, and inventory—ready for decisions.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/login"
                className="rounded-md bg-black px-5 py-3 text-white hover:opacity-90 text-center"
              >
                Start now
              </Link>
              <a
                href="#features"
                className="rounded-md border px-5 py-3 text-center hover:bg-gray-50"
              >
                Explore features
              </a>
            </div>
            <div className="flex items-center gap-5 pt-4 text-xs text-gray-500">
              <div className="flex -space-x-2">
                <span className="inline-block h-6 w-6 rounded-full bg-gray-200" />
                <span className="inline-block h-6 w-6 rounded-full bg-gray-200" />
                <span className="inline-block h-6 w-6 rounded-full bg-gray-200" />
              </div>
              <span>Trusted by SMBs across Lebanon</span>
            </div>
          </div>
          <div className="relative">
            <div className="mx-auto h-72 w-full max-w-md rounded-xl border bg-white shadow-sm md:h-96">
              {/* Placeholder “screenshot” card */}
              <div className="h-10 w-full rounded-t-xl border-b bg-gray-50" />
              <div className="p-5 space-y-4">
                <div className="h-6 w-40 rounded-md bg-gray-200" />
                <div className="grid grid-cols-3 gap-3">
                  <div className="h-28 rounded-md border" />
                  <div className="h-28 rounded-md border" />
                  <div className="h-28 rounded-md border" />
                </div>
                <div className="h-6 w-24 rounded-md bg-gray-200" />
                <div className="h-28 rounded-md border" />
              </div>
            </div>
            <div className="pointer-events-none absolute -bottom-6 -right-6 hidden h-28 w-28 rotate-6 rounded-lg border bg-white shadow-md md:block" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold">Why Hissabi</h2>
          <p className="mt-2 max-w-2xl text-gray-600">
            Built for real-world bookkeeping in Lebanon: multilingual data, messy spreadsheets, and fast answers.
          </p>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              {
                title: "Smart ingestion",
                desc: "LLM-assisted cleaning & labeling to standardize your sheets, even if headers are mixed or misspelled.",
              },
              {
                title: "Financial statements",
                desc: "Automatic Balance Sheet, P&L, and cash flow; export-ready PDFs for your records.",
              },
              {
                title: "Inventory summary",
                desc: "Track stock from documents—e.g., 10kg chicken, 3 dozen eggs—with consistent units and costs.",
              },
              {
                title: "Analytics",
                desc: "Trends and indicators across 1y / 6m / 3m / 1m—profitability, growth, burn, and more.",
              },
              {
                title: "Data security",
                desc: "Per-org isolation, role-based access, paywall enforcement, and encrypted storage.",
              },
              {
                title: "Scales with you",
                desc: "Clean architecture and API-first design. Plug into your tools as you grow.",
              },
            ].map((f) => (
              <div key={f.title} className="rounded-xl border bg-white p-5">
                <div className="mb-2 h-8 w-8 rounded-md bg-black" />
                <h3 className="font-medium">{f.title}</h3>
                <p className="mt-1 text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold">How it works</h2>
          <ol className="mt-6 grid gap-6 md:grid-cols-3">
            {[
              { step: "1", title: "Upload", desc: "Excel, CSV, or PDF. We parse and standardize automatically." },
              { step: "2", title: "Review", desc: "Check detected accounts, inventory items, and adjustments." },
              { step: "3", title: "Export", desc: "Get clean statements and analytics, ready to share." },
            ].map((s) => (
              <li key={s.step} className="rounded-xl border p-5">
                <div className="mb-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-black text-white">
                  {s.step}
                </div>
                <h3 className="font-medium">{s.title}</h3>
                <p className="mt-1 text-sm text-gray-600">{s.desc}</p>
              </li>
            ))}
          </ol>
          <div className="mt-8">
            <Link
              href="/login"
              className="inline-flex items-center rounded-md bg-black px-5 py-3 text-white hover:opacity-90"
            >
              Try it now
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing (placeholder) */}
      <section id="pricing" className="border-t bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold">Simple pricing</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {[
              { name: "Starter", price: "$0", desc: "Evaluate the workflow with sample data." },
              { name: "Pro", price: "$29/mo", desc: "For active SMBs—full features & priority support." },
              { name: "Business", price: "Contact", desc: "Custom SLAs, SSO, and data residency." },
            ].map((p) => (
              <div key={p.name} className="rounded-xl border bg-white p-6">
                <h3 className="text-lg font-medium">{p.name}</h3>
                <div className="mt-2 text-3xl font-semibold">{p.price}</div>
                <p className="mt-2 text-sm text-gray-600">{p.desc}</p>
                <Link
                  href="/login"
                  className="mt-6 inline-block rounded-md bg-black px-4 py-2 text-white hover:opacity-90"
                >
                  Get started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10 text-sm text-gray-600">
          <div className="flex flex-col justify-between gap-4 md:flex-row">
            <span>© {new Date().getFullYear()} Hissabi</span>
            <div className="flex gap-4">
              <a href="#" className="hover:opacity-70">Privacy</a>
              <a href="#" className="hover:opacity-70">Terms</a>
              <a href="#" className="hover:opacity-70">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
