// src/app/page.tsx
"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

// ============================================================================
// BUSINESS CONTENT
// ============================================================================
const businessFeatures = [
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

const businessSteps = [
  { step: "1", title: "Upload", desc: "Excel, CSV, or PDF. We parse and standardize automatically." },
  { step: "2", title: "Review", desc: "Check detected accounts, inventory items, and adjustments." },
  { step: "3", title: "Export", desc: "Get clean statements and analytics, ready to share." },
];

const businessPricing = [
  { name: "Starter", price: "$0", period: "/forever", desc: "Evaluate the workflow with sample data.", featured: false },
  { name: "Pro", price: "$29", period: "/month", desc: "For active SMBs—full features & priority support.", featured: true },
  { name: "Business", price: "Custom", period: "", desc: "Custom SLAs, SSO, and data residency.", featured: false },
];

// ============================================================================
// PERSONAL CONTENT
// ============================================================================
const personalFeatures = [
  {
    icon: "🧠",
    title: "AI Categorization",
    desc: "Just type 'paid $45 for dinner' and watch it auto-categorize with smart AI parsing.",
    gradient: "from-violet-500 to-purple-600",
  },
  {
    icon: "🌊",
    title: "The Flow",
    desc: "See exactly where your money goes with beautiful Sankey diagrams—from income to categories to merchants.",
    gradient: "from-cyan-500 to-blue-600",
  },
  {
    icon: "🏪",
    title: "Merchant DNA",
    desc: "Deep-dive into your spending habits at specific stores. Lifetime stats, visit patterns, price tracking.",
    gradient: "from-orange-500 to-red-600",
  },
  {
    icon: "💰",
    title: "Smart Budgets",
    desc: "Set limits per category, get real-time alerts. Visual progress bars keep you on track.",
    gradient: "from-emerald-500 to-green-600",
  },
  {
    icon: "💬",
    title: "AI Finance Chat",
    desc: "Ask 'How much did I spend on coffee this month?' and get instant, accurate answers.",
    gradient: "from-pink-500 to-rose-600",
  },
  {
    icon: "📈",
    title: "Trends & Insights",
    desc: "Weekly summaries, spending patterns, comparisons. AI-powered tips to improve your habits.",
    gradient: "from-amber-500 to-yellow-600",
  },
];

const personalSteps = [
  { step: "1", title: "Log", desc: "Type naturally or use the form. Our AI handles categorization." },
  { step: "2", title: "Explore", desc: "Visualize flows, browse merchants, track your budgets." },
  { step: "3", title: "Improve", desc: "Get personalized insights and make smarter decisions." },
];

const personalPricing = [
  { name: "Free", price: "$0", period: "/forever", desc: "Basic tracking with manual categories.", featured: false, features: ["50 entries/month", "Basic analytics", "1 budget"] },
  { name: "Pro", price: "$9", period: "/month", desc: "AI power + advanced analytics.", featured: true, features: ["Unlimited entries", "AI categorization", "Sankey Flow", "Merchant DNA", "Unlimited budgets", "AI Chat"] },
  { name: "Family", price: "$19", period: "/month", desc: "Coming soon—track together.", featured: false, features: ["Up to 5 members", "Shared budgets", "Family insights"] },
];

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [mode, setMode] = useState<"personal" | "business">("personal");

  useEffect(() => {
    setMounted(true);
  }, []);

  const isPersonal = mode === "personal";

  return (
    <main className={`min-h-screen ${isPersonal ? 'bg-slate-950 text-white' : 'bg-white text-gray-900'}`}>
      {/* Top nav */}
      <header className={`sticky top-0 z-50 border-b ${isPersonal ? 'border-slate-800 bg-slate-950/80' : 'border-slate-200 bg-white/80'} backdrop-blur-md`}>
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className={`h-9 w-9 rounded-xl ${isPersonal ? 'bg-gradient-to-br from-violet-500 to-purple-600' : 'bg-slate-900'} flex items-center justify-center group-hover:scale-105 transition-transform`}>
              <span className="text-white font-bold">H</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold tracking-tight text-lg">Hisabi</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isPersonal ? 'bg-violet-500/20 text-violet-300' : 'bg-slate-100 text-slate-600'}`}>
                {isPersonal ? 'Personal' : 'Business'}
              </span>
            </div>
          </Link>
          <nav className={`hidden md:flex items-center gap-8 text-sm ${isPersonal ? 'text-slate-400' : 'text-slate-600'}`}>
            <a href="#features" className={`hover:${isPersonal ? 'text-white' : 'text-slate-900'} transition-colors`}>Features</a>
            <a href="#how-it-works" className={`hover:${isPersonal ? 'text-white' : 'text-slate-900'} transition-colors`}>How it works</a>
            <a href="#pricing" className={`hover:${isPersonal ? 'text-white' : 'text-slate-900'} transition-colors`}>Pricing</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className={`text-sm ${isPersonal ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'} transition-colors`}>
              Sign in
            </Link>
            <Link
              href="/login"
              className={`rounded-xl px-5 py-2.5 text-sm font-medium transition-colors shadow-lg ${isPersonal
                  ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700 shadow-violet-500/25'
                  : 'bg-slate-900 text-white hover:bg-slate-800 shadow-slate-900/20'
                }`}
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Mode Toggle */}
      <div className="flex justify-center py-6">
        <div className={`inline-flex rounded-full p-1 ${isPersonal ? 'bg-slate-800' : 'bg-slate-100'}`}>
          <button
            onClick={() => setMode("personal")}
            className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${isPersonal
                ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-lg'
                : 'text-slate-600 hover:text-slate-900'
              }`}
          >
            Personal
          </button>
          <button
            onClick={() => setMode("business")}
            className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${!isPersonal
                ? 'bg-slate-900 text-white shadow-lg'
                : 'text-slate-400 hover:text-white'
              }`}
          >
            Business
          </button>
        </div>
      </div>

      {/* ======================================================================== */}
      {/* PERSONAL LANDING PAGE */}
      {/* ======================================================================== */}
      {isPersonal ? (
        <>
          {/* Hero - Personal */}
          <section className="relative overflow-hidden">
            {/* Animated gradient background */}
            <div className="absolute inset-0 -z-10">
              <div className="absolute top-0 -left-40 w-96 h-96 bg-violet-600/30 rounded-full blur-[128px] animate-pulse" />
              <div className="absolute top-40 right-0 w-80 h-80 bg-purple-600/20 rounded-full blur-[100px]" />
              <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-cyan-600/10 rounded-full blur-[100px]" />
            </div>

            <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 md:grid-cols-2 md:py-24">
              <div className={`space-y-8 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
                <div className="inline-flex items-center gap-2 rounded-full bg-violet-500/20 border border-violet-500/30 px-4 py-1.5 text-sm text-violet-300">
                  <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
                  New — AI-powered personal finance
                </div>
                <h1 className="text-4xl font-bold leading-tight md:text-5xl lg:text-6xl">
                  Your money.
                  <span className="block bg-gradient-to-r from-violet-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                    Your story.
                  </span>
                  <span className="block text-slate-400 text-3xl md:text-4xl lg:text-5xl font-normal">
                    Understood.
                  </span>
                </h1>
                <p className="text-lg text-slate-400 max-w-lg leading-relaxed">
                  Track expenses with AI, visualize your spending flows, discover merchant patterns,
                  and get personalized insights—all in one beautiful app.
                </p>
                <div className="flex flex-col gap-4 sm:flex-row">
                  <Link
                    href="/login"
                    className="rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 px-8 py-4 text-white text-center font-medium hover:from-violet-600 hover:to-purple-700 transition-all shadow-xl shadow-violet-500/25 hover:-translate-y-0.5"
                  >
                    Start tracking free
                  </Link>
                  <a
                    href="#features"
                    className="rounded-xl border-2 border-slate-700 px-8 py-4 text-center font-medium hover:bg-slate-800 hover:border-slate-600 transition-all"
                  >
                    See features
                  </a>
                </div>
              </div>

              {/* Hero Visual - Sankey Preview */}
              <div className={`relative ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`} style={{ animationDelay: '0.2s' }}>
                <div className="mx-auto max-w-md rounded-3xl border border-slate-700 bg-slate-900/50 backdrop-blur-xl shadow-2xl overflow-hidden">
                  <div className="h-10 border-b border-slate-700 bg-slate-800/50 flex items-center gap-2 px-4">
                    <div className="w-3 h-3 rounded-full bg-red-400/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400/80" />
                    <div className="w-3 h-3 rounded-full bg-green-400/80" />
                    <span className="ml-4 text-xs text-slate-500">The Flow</span>
                  </div>
                  <div className="p-6">
                    {/* Simplified Sankey Preview */}
                    <div className="flex items-center justify-between h-48">
                      {/* Income */}
                      <div className="flex flex-col gap-2">
                        <div className="h-20 w-3 rounded-full bg-gradient-to-b from-emerald-400 to-emerald-600" />
                        <span className="text-xs text-slate-500">Salary</span>
                      </div>
                      {/* Flow lines */}
                      <svg className="flex-1 h-full" viewBox="0 0 200 150">
                        <defs>
                          <linearGradient id="flow1" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.6" />
                            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.4" />
                          </linearGradient>
                          <linearGradient id="flow2" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#ec4899" stopOpacity="0.4" />
                          </linearGradient>
                          <linearGradient id="flow3" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.4" />
                          </linearGradient>
                        </defs>
                        <path d="M0,30 C100,30 100,20 200,20" stroke="url(#flow1)" strokeWidth="20" fill="none" opacity="0.8" />
                        <path d="M0,60 C100,60 100,75 200,75" stroke="url(#flow2)" strokeWidth="15" fill="none" opacity="0.8" />
                        <path d="M0,85 C100,85 100,130 200,130" stroke="url(#flow3)" strokeWidth="10" fill="none" opacity="0.8" />
                      </svg>
                      {/* Categories */}
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                          <div className="h-10 w-2 rounded-full bg-amber-500" />
                          <span className="text-xs text-slate-400">Food</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-8 w-2 rounded-full bg-pink-500" />
                          <span className="text-xs text-slate-400">Shopping</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-5 w-2 rounded-full bg-violet-500" />
                          <span className="text-xs text-slate-400">Transport</span>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-slate-700 flex justify-between text-sm">
                      <span className="text-slate-500">This month</span>
                      <span className="text-violet-400 font-medium">$3,240 tracked</span>
                    </div>
                  </div>
                </div>
                {/* Floating cards */}
                <div className="absolute -bottom-4 -left-4 w-40 rounded-xl border border-slate-700 bg-slate-800/80 backdrop-blur p-3 shadow-xl hidden md:block">
                  <div className="text-xs text-slate-400">Top Merchant</div>
                  <div className="font-semibold text-sm">Starbucks</div>
                  <div className="text-xs text-emerald-400">$124 this week</div>
                </div>
                <div className="absolute -top-4 -right-4 w-36 rounded-xl border border-violet-500/30 bg-violet-500/10 backdrop-blur p-3 shadow-xl hidden md:block">
                  <div className="text-xs text-violet-300">AI Insight</div>
                  <div className="text-xs text-slate-300">You spend 23% more on weekends</div>
                </div>
              </div>
            </div>
          </section>

          {/* Features - Personal */}
          <section id="features" className="border-t border-slate-800">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">Everything you need to master your money</h2>
                <p className="mt-4 text-lg text-slate-400">
                  Powered by AI. Designed for humans who want to understand their spending.
                </p>
              </div>
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {personalFeatures.map((f, index) => (
                  <div
                    key={f.title}
                    className={`group rounded-2xl border border-slate-800 bg-slate-900/50 p-6 hover:border-slate-700 hover:bg-slate-800/50 transition-all duration-300 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <div className={`mb-4 w-12 h-12 rounded-xl bg-gradient-to-br ${f.gradient} flex items-center justify-center text-2xl shadow-lg group-hover:scale-110 transition-transform`}>
                      {f.icon}
                    </div>
                    <h3 className="font-semibold text-lg">{f.title}</h3>
                    <p className="mt-2 text-slate-400 leading-relaxed">{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* How it works - Personal */}
          <section id="how-it-works" className="border-t border-slate-800">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">Simple as 1-2-3</h2>
                <p className="mt-4 text-lg text-slate-400">
                  No spreadsheets. No manual tagging. Just you and your data.
                </p>
              </div>
              <div className="grid gap-8 md:grid-cols-3">
                {personalSteps.map((s, index) => (
                  <div key={s.step} className="relative">
                    {index < personalSteps.length - 1 && (
                      <div className="hidden md:block absolute top-10 left-full w-full h-0.5 bg-gradient-to-r from-violet-500 to-transparent -translate-x-1/2" />
                    )}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8 text-center hover:border-violet-500/50 hover:shadow-lg hover:shadow-violet-500/10 transition-all">
                      <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 text-white text-2xl font-bold flex items-center justify-center shadow-lg shadow-violet-500/25">
                        {s.step}
                      </div>
                      <h3 className="font-semibold text-xl">{s.title}</h3>
                      <p className="mt-2 text-slate-400">{s.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-12 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 px-8 py-4 text-white font-medium hover:from-violet-600 hover:to-purple-700 transition-all shadow-xl shadow-violet-500/25"
                >
                  Try it now
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </Link>
              </div>
            </div>
          </section>

          {/* Pricing - Personal */}
          <section id="pricing" className="border-t border-slate-800">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">Start free, upgrade when ready</h2>
                <p className="mt-4 text-lg text-slate-400">
                  No credit card required. Cancel anytime.
                </p>
              </div>
              <div className="grid gap-8 md:grid-cols-3">
                {personalPricing.map((p) => (
                  <div
                    key={p.name}
                    className={`rounded-2xl border p-8 ${p.featured
                      ? 'border-violet-500 bg-gradient-to-b from-violet-500/10 to-purple-500/5 shadow-2xl shadow-violet-500/20 scale-105'
                      : 'border-slate-800 bg-slate-900/50'
                      }`}
                  >
                    {p.featured && (
                      <div className="inline-block px-3 py-1 rounded-full bg-violet-500 text-white text-xs font-medium mb-4">
                        Most Popular
                      </div>
                    )}
                    <h3 className="text-xl font-semibold">{p.name}</h3>
                    <div className="mt-4 flex items-baseline gap-1">
                      <span className="text-4xl font-bold">{p.price}</span>
                      <span className="text-slate-400">{p.period}</span>
                    </div>
                    <p className="mt-4 text-slate-400">{p.desc}</p>
                    <ul className="mt-6 space-y-3">
                      {p.features.map((f) => (
                        <li key={f} className="flex items-center gap-2 text-sm">
                          <svg className={`w-5 h-5 ${p.featured ? 'text-violet-400' : 'text-slate-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          {f}
                        </li>
                      ))}
                    </ul>
                    <Link
                      href="/login"
                      className={`mt-8 block w-full rounded-xl px-4 py-3 text-center font-medium transition-all ${p.featured
                        ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                        : 'bg-slate-800 text-white hover:bg-slate-700'
                        }`}
                    >
                      Get started
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* CTA - Personal */}
          <section className="border-t border-slate-800">
            <div className="mx-auto max-w-4xl px-4 py-20 text-center">
              <h2 className="text-3xl font-bold">Ready to understand your spending?</h2>
              <p className="mt-4 text-lg text-slate-400">
                Join thousands tracking their finances with AI-powered insights.
              </p>
              <Link
                href="/login"
                className="mt-8 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 px-10 py-4 text-white font-medium hover:from-violet-600 hover:to-purple-700 transition-all shadow-xl shadow-violet-500/25 hover:-translate-y-0.5"
              >
                Start for free
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </Link>
            </div>
          </section>

          {/* Footer - Personal */}
          <footer className="border-t border-slate-800 bg-slate-900">
            <div className="mx-auto max-w-6xl px-4 py-12">
              <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">H</span>
                  </div>
                  <div>
                    <span className="font-semibold">Hisabi Personal</span>
                    <span className="block text-xs text-slate-400">Your AI Finance Companion</span>
                  </div>
                </div>
                <div className="flex gap-8 text-sm text-slate-400">
                  <a href="#" className="hover:text-white transition-colors">Privacy</a>
                  <a href="#" className="hover:text-white transition-colors">Terms</a>
                  <a href="#" className="hover:text-white transition-colors">Contact</a>
                </div>
                <span className="text-sm text-slate-400">© {new Date().getFullYear()} Hisabi</span>
              </div>
            </div>
          </footer>
        </>
      ) : (
        /* ======================================================================== */
        /* BUSINESS LANDING PAGE (Original) */
        /* ======================================================================== */
        <>
          {/* Hero - Business */}
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
                  Hisabi cleans, analyzes, and generates balance sheets, P&L, and inventory—ready for decisions.
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
                    <span className="font-semibold text-slate-900">100+</span> SMBs trust Hisabi
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
                    <span className="ml-4 text-xs text-slate-500">dashboard.hisabi.com</span>
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

          {/* Features - Business */}
          <section id="features" className="border-t bg-slate-50">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">Why Hisabi</h2>
                <p className="mt-4 text-lg text-slate-600">
                  Built for real-world bookkeeping in Lebanon: multilingual data, messy spreadsheets, and fast answers.
                </p>
              </div>
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {businessFeatures.map((f, index) => (
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

          {/* How it works - Business */}
          <section id="how-it-works" className="border-t">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">How it works</h2>
                <p className="mt-4 text-lg text-slate-600">
                  Three simple steps to clean, organized financial data.
                </p>
              </div>
              <div className="grid gap-8 md:grid-cols-3">
                {businessSteps.map((s, index) => (
                  <div key={s.step} className="relative">
                    {index < businessSteps.length - 1 && (
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

          {/* Pricing - Business */}
          <section id="pricing" className="border-t bg-slate-50">
            <div className="mx-auto max-w-6xl px-4 py-20">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold">Simple, transparent pricing</h2>
                <p className="mt-4 text-lg text-slate-600">
                  Start free, upgrade when you&apos;re ready. No hidden fees.
                </p>
              </div>
              <div className="grid gap-8 md:grid-cols-3">
                {businessPricing.map((p) => (
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

          {/* CTA - Business */}
          <section className="border-t">
            <div className="mx-auto max-w-4xl px-4 py-20 text-center">
              <h2 className="text-3xl font-bold">Ready to simplify your accounting?</h2>
              <p className="mt-4 text-lg text-slate-600">
                Join 100+ Lebanese SMBs already using Hisabi to save time and make better decisions.
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

          {/* Footer - Business */}
          <footer className="border-t bg-slate-900 text-white">
            <div className="mx-auto max-w-6xl px-4 py-12">
              <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center">
                    <span className="text-slate-900 font-bold text-lg">H</span>
                  </div>
                  <div>
                    <span className="font-semibold">Hisabi</span>
                    <span className="block text-xs text-slate-400">SMB Accounting for Lebanon</span>
                  </div>
                </div>
                <div className="flex gap-8 text-sm text-slate-400">
                  <a href="#" className="hover:text-white transition-colors">Privacy</a>
                  <a href="#" className="hover:text-white transition-colors">Terms</a>
                  <a href="#" className="hover:text-white transition-colors">Contact</a>
                </div>
                <span className="text-sm text-slate-400">© {new Date().getFullYear()} Hisabi</span>
              </div>
            </div>
          </footer>
        </>
      )}
    </main>
  );
}
