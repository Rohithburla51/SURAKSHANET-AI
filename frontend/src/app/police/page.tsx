"use client";

/**
 * frontend/src/app/police/page.tsx
 * ─────────────────────────────────
 * SurakshaNet AI — Police Intelligence Dashboard
 * Phase 5: Advanced CDN Visualizations
 * Model: Claude Sonnet 4.6 (1.3x)
 *
 * Sidebar (controls) + full-height vis-network graph area.
 * Three query modes: NL search, phone trace, bank account trace.
 */

import React, { useCallback, useState } from "react";
import {
  queryNetwork,
  tracePhone,
  traceAccount,
  type NetworkQueryResult,
} from "@/lib/api";
import NetworkGraph from "@/components/NetworkGraph";

// ─────────────────────────────────────────────────────────────────────────────
// Spinner
// ─────────────────────────────────────────────────────────────────────────────

function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo queries
// ─────────────────────────────────────────────────────────────────────────────

const DEMO_QUERIES = [
  "Find all mule accounts connected to Operator Alpha",
  "Show me the full network around phone +919876543210",
  "Which victims lost more than ₹5 lakh to the Jharkhand ring?",
  "List all FraudActors operating from Bihar",
];

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function PolicePage() {
  // ── State ─────────────────────────────────────────────────────────────────
  const [nlQuery,    setNlQuery]    = useState("");
  const [phoneNum,   setPhoneNum]   = useState("");
  const [accountId,  setAccountId]  = useState("");
  const [hops,       setHops]       = useState(3);
  const [loading,    setLoading]    = useState(false);
  const [result,     setResult]     = useState<NetworkQueryResult | null>(null);
  const [error,      setError]      = useState<string | null>(null);
  const [activeTab,  setActiveTab]  = useState<"nl" | "phone" | "account">("nl");

  // ── Submit handlers ─────────────────────────────────────────────────────

  const runQuery = useCallback(async (fetcher: () => Promise<NetworkQueryResult>) => {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await fetcher();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleNlSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const q = nlQuery.trim();
    if (!q) { setError("Enter a question."); return; }
    runQuery(() => queryNetwork(q));
  }, [nlQuery, runQuery]);

  const handlePhoneSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const num = phoneNum.trim();
    if (!num) { setError("Enter a phone number."); return; }
    runQuery(() => tracePhone(num, hops));
  }, [phoneNum, hops, runQuery]);

  const handleAccountSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const aid = accountId.trim();
    if (!aid) { setError("Enter a bank account ID."); return; }
    runQuery(() => traceAccount(aid, hops));
  }, [accountId, hops, runQuery]);

  const handleDemoClick = useCallback((q: string) => {
    setNlQuery(q);
    setActiveTab("nl");
    runQuery(() => queryNetwork(q));
  }, [runQuery]);

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <div className="flex flex-col lg:flex-row min-h-screen">

        {/* ═══════════════════════════════════════════════════════════════════
            LEFT SIDEBAR — Controls
        ═══════════════════════════════════════════════════════════════════ */}
        <aside className="w-full lg:w-80 xl:w-96 shrink-0 border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-900/60 p-5 space-y-6 overflow-y-auto lg:max-h-screen">

          {/* Header */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <svg className="w-6 h-6 text-indigo-400 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                <path d="M12 1L3 5v6c0 5.25 3.75 10.15 9 11.35C17.25 21.15 21 16.25 21 11V5l-9-4z"/>
              </svg>
              <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
                SurakshaNet AI
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight">Police Intelligence</h1>
            <p className="text-xs text-slate-500 leading-relaxed">
              Natural-language graph queries against the fraud intelligence database.
            </p>
          </div>

          {/* ── Tabs ───────────────────────────────────────────────────────── */}
          <div role="tablist" className="flex gap-1 p-1 bg-slate-800/60 rounded-xl">
            {([
              { id: "nl",      label: "🔍 NL Query"  },
              { id: "phone",   label: "📱 Phone"     },
              { id: "account", label: "🏦 Account"   },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => { setActiveTab(tab.id); setError(null); }}
                className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors text-center ${
                  activeTab === tab.id
                    ? "bg-slate-700 text-slate-100 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── NL Query Panel ─────────────────────────────────────────────── */}
          {activeTab === "nl" && (
            <form onSubmit={handleNlSubmit} className="space-y-3">
              <label htmlFor="nl-input" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Ask in plain English
              </label>
              <textarea
                id="nl-input"
                value={nlQuery}
                onChange={(e) => { setNlQuery(e.target.value); setError(null); }}
                placeholder="e.g. Find all mules connected to Operator Alpha"
                rows={3}
                maxLength={1000}
                disabled={loading}
                className="w-full rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100
                           placeholder-slate-600 text-sm px-3 py-2.5 resize-none
                           focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500
                           transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !nlQuery.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                           bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                           disabled:opacity-40 disabled:cursor-not-allowed
                           text-white text-sm font-semibold transition-colors"
              >
                {loading ? <><Spinner /> Querying…</> : "Execute Query"}
              </button>

              {/* Quick demo queries */}
              <div className="space-y-1.5 pt-2">
                <h4 className="text-[10px] uppercase tracking-widest text-slate-600 font-semibold">
                  Quick Demos
                </h4>
                <div className="flex flex-col gap-1.5">
                  {DEMO_QUERIES.map((q) => (
                    <button
                      key={q}
                      type="button"
                      disabled={loading}
                      onClick={() => handleDemoClick(q)}
                      className="text-left text-xs text-slate-500 hover:text-indigo-400
                                 transition-colors truncate disabled:opacity-40"
                      title={q}
                    >
                      → {q}
                    </button>
                  ))}
                </div>
              </div>
            </form>
          )}

          {/* ── Phone Trace Panel ──────────────────────────────────────────── */}
          {activeTab === "phone" && (
            <form onSubmit={handlePhoneSubmit} className="space-y-3">
              <label htmlFor="phone-input" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Phone Number
              </label>
              <input
                id="phone-input"
                type="text"
                value={phoneNum}
                onChange={(e) => { setPhoneNum(e.target.value); setError(null); }}
                placeholder="+919876543210"
                maxLength={20}
                disabled={loading}
                className="w-full rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100
                           placeholder-slate-600 text-sm px-3 py-2.5
                           focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500
                           transition-colors"
              />
              <div className="space-y-1">
                <label htmlFor="phone-hops" className="text-xs text-slate-500">
                  Traversal depth: {hops} hop{hops > 1 ? "s" : ""}
                </label>
                <input
                  id="phone-hops"
                  type="range"
                  min={1} max={4} step={1}
                  value={hops}
                  onChange={(e) => setHops(Number(e.target.value))}
                  disabled={loading}
                  className="w-full accent-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !phoneNum.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                           bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                           disabled:opacity-40 disabled:cursor-not-allowed
                           text-white text-sm font-semibold transition-colors"
              >
                {loading ? <><Spinner /> Tracing…</> : "Trace Network"}
              </button>
            </form>
          )}

          {/* ── Account Trace Panel ────────────────────────────────────────── */}
          {activeTab === "account" && (
            <form onSubmit={handleAccountSubmit} className="space-y-3">
              <label htmlFor="account-input" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Bank Account ID
              </label>
              <input
                id="account-input"
                type="text"
                value={accountId}
                onChange={(e) => { setAccountId(e.target.value); setError(null); }}
                placeholder="SBI-XXXX1234"
                maxLength={50}
                disabled={loading}
                className="w-full rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100
                           placeholder-slate-600 text-sm px-3 py-2.5
                           focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500
                           transition-colors"
              />
              <div className="space-y-1">
                <label htmlFor="acct-hops" className="text-xs text-slate-500">
                  Traversal depth: {hops} hop{hops > 1 ? "s" : ""}
                </label>
                <input
                  id="acct-hops"
                  type="range"
                  min={1} max={4} step={1}
                  value={hops}
                  onChange={(e) => setHops(Number(e.target.value))}
                  disabled={loading}
                  className="w-full accent-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !accountId.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                           bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                           disabled:opacity-40 disabled:cursor-not-allowed
                           text-white text-sm font-semibold transition-colors"
              >
                {loading ? <><Spinner /> Tracing…</> : "Trace Network"}
              </button>
            </form>
          )}

          {/* ── Error display ──────────────────────────────────────────────── */}
          {error && (
            <p role="alert" className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* ── Safety notice ──────────────────────────────────────────────── */}
          {result && !result.is_safe && (
            <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
              ⚠ Query rejected — read-only access only.
            </div>
          )}

        </aside>


        {/* ═══════════════════════════════════════════════════════════════════
            RIGHT — Visualization Area
        ═══════════════════════════════════════════════════════════════════ */}
        <section className="flex-1 p-4 lg:p-6 overflow-y-auto space-y-4 lg:max-h-screen">

          {/* Loading state */}
          {loading && !result && (
            <div className="flex items-center justify-center h-96 rounded-xl border border-slate-800 bg-slate-900/30">
              <div className="flex flex-col items-center gap-3">
                <Spinner className="h-8 w-8 text-indigo-400" />
                <p className="text-sm text-slate-500">
                  Translating query & traversing graph…
                </p>
              </div>
            </div>
          )}

          {/* Result graph */}
          {result && <NetworkGraph result={result} />}

          {/* Empty state */}
          {!loading && !result && (
            <div className="flex flex-col items-center justify-center h-96 rounded-xl border border-slate-800 bg-slate-900/30 gap-3">
              <svg className="w-14 h-14 text-slate-800" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                <circle cx="6" cy="12" r="2.5"/>
                <circle cx="18" cy="7" r="2.5"/>
                <circle cx="18" cy="17" r="2.5"/>
                <path d="M8.5 11.2l7 -3.4M8.5 12.8l7 3.4" stroke="currentColor" strokeWidth="1" fill="none"/>
              </svg>
              <p className="text-sm text-slate-700 text-center max-w-xs">
                Enter a natural language query, phone number, or bank account to
                visualise the connected fraud network.
              </p>
            </div>
          )}

        </section>

      </div>
    </main>
  );
}
