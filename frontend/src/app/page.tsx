"use client";

/**
 * frontend/src/app/page.tsx
 * ───────────────────────────
 * SurakshaNet AI — Unified Root Page
 * Merges Citizen Safety Portal and Bank Teller Scanner into a single
 * segmented-control tab interface.
 */

import React, { useState } from "react";
import CitizenPortal from "@/components/CitizenPortal";
import BankPortal    from "@/components/BankPortal";

type Tab = "citizen" | "bank";

const TABS: { id: Tab; label: string; icon: React.ReactNode; accent: string }[] = [
  {
    id: "citizen",
    label: "Citizen Reporting",
    accent: "indigo",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M12 1L3 5v6c0 5.25 3.75 10.15 9 11.35C17.25 21.15 21 16.25 21 11V5l-9-4z" />
      </svg>
    ),
  },
  {
    id: "bank",
    label: "Bank Teller Scanner",
    accent: "amber",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm0 2v12h16V6H4zm2 2h2v2H6V8zm10 0h2v2h-2V8zm-5 2a3 3 0 110 6 3 3 0 010-6z" />
      </svg>
    ),
  },
];

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<Tab>("citizen");

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 px-4 py-10">
      <div className="mx-auto max-w-5xl w-full space-y-8">

        {/* ── Brand header ─────────────────────────────────────────────────── */}
        <header className="flex items-center gap-3">
          <svg className="w-8 h-8 text-indigo-400 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 1L3 5v6c0 5.25 3.75 10.15 9 11.35C17.25 21.15 21 16.25 21 11V5l-9-4z" />
          </svg>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400 leading-none mb-0.5">
              SurakshaNet AI
            </p>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight leading-none">
              India&rsquo;s Unified Fraud Intelligence Platform
            </h1>
          </div>
        </header>

        {/* ── Segmented tab control ─────────────────────────────────────────── */}
        <div
          role="tablist"
          aria-label="Portal selector"
          className="flex gap-1 p-1.5 bg-slate-900 border border-slate-800 rounded-2xl w-fit shadow-lg"
        >
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            const activeStyles =
              tab.id === "citizen"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-900/40"
                : "bg-amber-500 text-slate-950 shadow-md shadow-amber-900/40";
            const inactiveStyles = "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60";

            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls={`panel-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  isActive ? activeStyles : inactiveStyles
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* ── Tab panels ────────────────────────────────────────────────────── */}
        <div
          id="panel-citizen"
          role="tabpanel"
          aria-labelledby="tab-citizen"
          hidden={activeTab !== "citizen"}
        >
          {activeTab === "citizen" && <CitizenPortal />}
        </div>

        <div
          id="panel-bank"
          role="tabpanel"
          aria-labelledby="tab-bank"
          hidden={activeTab !== "bank"}
        >
          {activeTab === "bank" && <BankPortal />}
        </div>

      </div>
    </main>
  );
}
