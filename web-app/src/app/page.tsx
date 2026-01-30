// src/app/page.tsx
"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

const features = [
  {
    icon: "🧠",
    title: "Smart Ingestion",
    desc: "LLM-assisted cleaning & labeling to standardize your sheets, even if headers are mixed or misspelled.",
  },
  {
    icon: "📊",
    title: "Financial Statements",
    desc: "Automatic Balance Sheet, P&L, and cash flow; export-ready PDFs for your records.",
  },
  {
    icon: "💬",
    title: "Instant Answers",
    desc: "Ask questions like 'How much did we spend on marketing?' and get instant, accurate answers from your data.",
  },
  {
    icon: "📈",
    title: "Analytics Dashboard",
    desc: "Trends and indicators across 1y / 6m / 3m / 1m—profitability, growth, and more.",
  },
  {
    icon: "🔐",
    title: "Data Security",
    desc: "Per-org isolation, role-based access, paywall enforcement, and encrypted storage.",
  },
  {
    icon: "🚀",
    title: "Scales With You",
    desc: "Clean architecture and API-first design. Plug into your tools as you grow.",
  },
];

const steps = [
  { step: "1", title: "Upload", desc: "Excel, CSV, or PDF. We parse and standardize automatically." },
  { step: "2", title: "Review", desc: "Check detected accounts, inventory items, and adjustments." },
  { step: "3", title: "Export", desc: "Get clean statements and analytics, ready to share." },
];

const pricing = [
  { name: "Starter", price: "$0", period: "/forever", desc: "Evaluate the workflow with sample data.", featured: false },
  { name: "Pro", price: "$29", period: "/month", desc: "For active SMBs—full features & priority support.", featured: true },
  { name: "Business", price: "Custom", period: "", desc: "Custom SLAs, SSO, and data residency.", featured: false },
];

export default function HomePage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <main className="min-h-screen bg-white text-gray-900">
      {/* Top nav */}
      <header className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-md">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="h-9 w-9 rounded-xl bg-slate-900 flex items-center justify-center group-hover:scale-105 transition-transform">
              <span className="text-white font-bold">H</span>
            </div>
            <span className="font-semibold tracking-tight text-lg">Hissabi</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm">
            <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">Features</a>
            <a href="#how-it-works" className="text-slate-600 hover:text-slate-900 transition-colors">How it works</a>
            <a href="#pricing" className="text-slate-600 hover:text-slate-900 transition-colors">Pricing</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
              Sign in
            </Link>
            <Link
              href="/login"
              className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-800 transition-colors shadow-lg shadow-slate-900/20"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-emerald-50/30 -z-10" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-100/50 rounded-full blur-3xl -z-10" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-slate-100 rounded-full blur-3xl -z-10" />

        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 md:grid-cols-2 md:py-32">
          <div className={`space-y-8 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-4 py-1.5 text-sm text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Now in beta — free to try
            </div>
            <h1 className="text-4xl font-bold leading-tight md:text-5xl lg:text-6xl">
              Accounting that
              <span className="block text-gradient">speaks your language.</span>
            </h1>
            <p className="text-lg text-slate-600 max-w-lg leading-relaxed">
              Upload your business documents (even messy, mixed-language sheets).
              Hissabi cleans, analyzes, and generates balance sheets, P&L, and inventory—ready for decisions.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row">
              <Link
                href="/login"
                className="rounded-xl bg-slate-900 px-8 py-4 text-white text-center font-medium hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/25 hover:-translate-y-0.5"
              >
                Start for free
              </Link>
              <a
                href="#features"
                className="rounded-xl border-2 border-slate-200 px-8 py-4 text-center font-medium hover:bg-slate-50 hover:border-slate-300 transition-all"
              >
                Explore features
              </a>
            </div>
            <div className="flex items-center gap-6 pt-4">
              <div className="flex -space-x-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 border-2 border-white" />
                ))}
              </div>
              <div className="text-sm text-slate-600">
                <span className="font-semibold text-slate-900">100+</span> SMBs trust Hissabi
              </div>
            </div>
          </div>

          {/* Hero Card */}
          <div className={`relative ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`} style={{ animationDelay: '0.2s' }}>
            <div className="mx-auto max-w-md rounded-2xl border bg-white shadow-2xl shadow-slate-200/50 overflow-hidden">
              <div className="h-12 border-b bg-slate-50 flex items-center gap-2 px-4">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="ml-4 text-xs text-slate-500">dashboard.hissabi.com</span>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="h-6 w-32 rounded-md bg-slate-200" />
                  <div className="h-6 w-20 rounded-md bg-emerald-100" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border p-4 space-y-2">
                    <div className="h-3 w-16 rounded bg-slate-200" />
                    <div className="h-6 w-24 rounded bg-emerald-200" />
                  </div>
                  <div className="rounded-xl border p-4 space-y-2">
                    <div className="h-3 w-16 rounded bg-slate-200" />
                    <div className="h-6 w-20 rounded bg-rose-200" />
                  </div>
                </div>
                <div className="rounded-xl border p-4 h-32 flex items-end gap-2">
                  {[60, 80, 45, 90, 70, 85].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="absolute -bottom-4 -right-4 w-32 h-32 rounded-2xl border bg-white shadow-xl rotate-6 hidden md:block" />
            <div className="absolute -top-4 -left-4 w-24 h-24 rounded-2xl bg-emerald-100 -rotate-12 hidden md:block" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold">Why Hissabi</h2>
            <p className="mt-4 text-lg text-slate-600">
              Built for real-world bookkeeping in Lebanon: multilingual data, messy spreadsheets, and fast answers.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((f, index) => (
              <div
                key={f.title}
                className={`rounded-2xl border bg-white p-6 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="mb-4 w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center text-2xl">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-lg">{f.title}</h3>
                <p className="mt-2 text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold">How it works</h2>
            <p className="mt-4 text-lg text-slate-600">
              Three simple steps to clean, organized financial data.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {steps.map((s, index) => (
              <div key={s.step} className="relative">
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-full w-full h-0.5 bg-slate-200 -translate-x-1/2" />
                )}
                <div className="rounded-2xl border p-8 text-center hover:shadow-lg transition-shadow">
                  <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-slate-900 text-white text-2xl font-bold flex items-center justify-center">
                    {s.step}
                  </div>
                  <h3 className="font-semibold text-xl">{s.title}</h3>
                  <p className="mt-2 text-slate-600">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-8 py-4 text-white font-medium hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/20"
            >
              Try it now
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold">Simple, transparent pricing</h2>
            <p className="mt-4 text-lg text-slate-600">
              Start free, upgrade when you&apos;re ready. No hidden fees.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {pricing.map((p) => (
              <div
                key={p.name}
                className={`rounded-2xl border p-8 ${p.featured
                  ? 'bg-slate-900 text-white border-slate-900 shadow-2xl shadow-slate-900/30 scale-105'
                  : 'bg-white'
                  }`}
              >
                {p.featured && (
                  <div className="inline-block px-3 py-1 rounded-full bg-emerald-500 text-white text-xs font-medium mb-4">
                    Most Popular
                  </div>
                )}
                <h3 className={`text-xl font-semibold ${p.featured ? 'text-white' : ''}`}>{p.name}</h3>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-bold">{p.price}</span>
                  <span className={p.featured ? 'text-slate-400' : 'text-slate-500'}>{p.period}</span>
                </div>
                <p className={`mt-4 ${p.featured ? 'text-slate-300' : 'text-slate-600'}`}>{p.desc}</p>
                <Link
                  href="/login"
                  className={`mt-8 block w-full rounded-xl px-4 py-3 text-center font-medium transition-all ${p.featured
                    ? 'bg-white text-slate-900 hover:bg-slate-100'
                    : 'bg-slate-900 text-white hover:bg-slate-800'
                    }`}
                >
                  Get started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-3xl font-bold">Ready to simplify your accounting?</h2>
          <p className="mt-4 text-lg text-slate-600">
            Join 100+ Lebanese SMBs already using Hissabi to save time and make better decisions.
          </p>
          <Link
            href="/login"
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-10 py-4 text-white font-medium hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/20 hover:-translate-y-0.5"
          >
            Start for free
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-slate-900 text-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center">
                <span className="text-slate-900 font-bold text-lg">H</span>
              </div>
              <div>
                <span className="font-semibold">Hissabi</span>
                <span className="block text-xs text-slate-400">SMB Accounting for Lebanon</span>
              </div>
            </div>
            <div className="flex gap-8 text-sm text-slate-400">
              <a href="#" className="hover:text-white transition-colors">Privacy</a>
              <a href="#" className="hover:text-white transition-colors">Terms</a>
              <a href="#" className="hover:text-white transition-colors">Contact</a>
            </div>
            <span className="text-sm text-slate-400">© {new Date().getFullYear()} Hissabi</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
