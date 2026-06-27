"use client";

/**
 * frontend/src/components/RiskScore.tsx
 * ──────────────────────────────────────
 * Animated circular SVG risk gauge + full analysis breakdown.
 * Zero external charting dependencies — pure SVG math.
 */

import React, { useEffect, useRef, useState } from "react";
import type { ScamAnalysisResult } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function scoreColor(score: number): { stroke: string; text: string; glow: string; bg: string } {
  if (score > 70)
    return {
      stroke: "#ef4444",   // red-500
      text:   "text-red-400",
      glow:   "drop-shadow(0 0 12px rgba(239,68,68,0.7))",
      bg:     "bg-red-500/10 border-red-500/30",
    };
  if (score >= 40)
    return {
      stroke: "#f59e0b",   // amber-500
      text:   "text-amber-400",
      glow:   "drop-shadow(0 0 12px rgba(245,158,11,0.7))",
      bg:     "bg-amber-500/10 border-amber-500/30",
    };
  return {
    stroke: "#22c55e",   // green-500
    text:   "text-green-400",
    glow:   "drop-shadow(0 0 12px rgba(34,197,94,0.7))",
    bg:     "bg-green-500/10 border-green-500/30",
  };
}

function verdictLabel(verdict: string): { label: string; className: string } {
  switch (verdict) {
    case "SCAM":
      return { label: "⛔ SCAM DETECTED",    className: "bg-red-500/20    text-red-300    border-red-500/40"    };
    case "LIKELY_SCAM":
      return { label: "⚠️ LIKELY SCAM",      className: "bg-amber-500/20  text-amber-300  border-amber-500/40"  };
    case "SAFE":
      return { label: "✅ APPEARS SAFE",     className: "bg-green-500/20  text-green-300  border-green-500/40"  };
    default:
      return { label: "🔍 UNCERTAIN",        className: "bg-slate-500/20  text-slate-300  border-slate-500/40"  };
  }
}

function slugToLabel(slug: string): string {
  return slug
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─────────────────────────────────────────────────────────────────────────────
// Circular SVG Gauge
// ─────────────────────────────────────────────────────────────────────────────

interface GaugeProps {
  score: number;       // 0–100
  animated?: boolean;
}

function CircularGauge({ score, animated = true }: GaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const colors       = scoreColor(clampedScore);

  // SVG arc math
  const radius        = 72;
  const cx            = 90;
  const cy            = 90;
  const circumference = 2 * Math.PI * radius;
  const arcLength     = (clampedScore / 100) * circumference;

  // Animated count-up
  const [displayScore, setDisplayScore] = useState(animated ? 0 : clampedScore);
  const [dashOffset, setDashOffset]     = useState(circumference);
  const rafRef                           = useRef<number | null>(null);

  useEffect(() => {
    if (!animated) {
      setDisplayScore(clampedScore);
      setDashOffset(circumference - arcLength);
      return;
    }

    const duration = 900; // ms
    const start    = performance.now();

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(eased * clampedScore));
      setDashOffset(circumference - eased * arcLength);
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [clampedScore, animated, arcLength, circumference]);

  return (
    <svg
      width={180}
      height={180}
      viewBox="0 0 180 180"
      className="mx-auto"
      aria-label={`Risk score ${clampedScore} out of 100`}
    >
      {/* Track ring */}
      <circle
        cx={cx} cy={cy} r={radius}
        fill="none"
        stroke="#1e293b"
        strokeWidth={12}
      />
      {/* Score arc — starts at 12 o'clock, goes clockwise */}
      <circle
        cx={cx} cy={cy} r={radius}
        fill="none"
        stroke={colors.stroke}
        strokeWidth={12}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{
          filter: colors.glow,
          transition: animated ? undefined : "none",
        }}
      />
      {/* Centre score */}
      <text
        x={cx} y={cy - 8}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={38}
        fontWeight={700}
        fontFamily="system-ui, sans-serif"
        fill={colors.stroke}
      >
        {displayScore}
      </text>
      {/* "/100" label */}
      <text
        x={cx} y={cy + 22}
        textAnchor="middle"
        fontSize={12}
        fontFamily="system-ui, sans-serif"
        fill="#64748b"
      >
        / 100
      </text>
      {/* "RISK" label */}
      <text
        x={cx} y={cy + 38}
        textAnchor="middle"
        fontSize={10}
        fontFamily="system-ui, sans-serif"
        fill="#475569"
        letterSpacing={2}
      >
        RISK
      </text>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Chip arrays
// ─────────────────────────────────────────────────────────────────────────────

function ChipArray({ items, colorClass }: { items: string[]; colorClass: string }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className={`px-3 py-1 rounded-full text-xs font-medium border ${colorClass}`}
        >
          {slugToLabel(item)}
        </span>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main exported component
// ─────────────────────────────────────────────────────────────────────────────

interface RiskScoreProps {
  result: ScamAnalysisResult;
}

export default function RiskScore({ result }: RiskScoreProps) {
  const colors  = scoreColor(result.risk_score ?? 0);
  const verdict = verdictLabel(result.verdict ?? "UNCERTAIN");
  const confidencePct = Math.round((result.confidence ?? 0) * 100);

  // Defensive array access — never break if backend sends null/undefined
  const tactics = Array.isArray(result.manipulation_tactics) ? result.manipulation_tactics : [];
  const flags   = Array.isArray(result.red_flags) ? result.red_flags : [];
  const actions = Array.isArray(result.recommended_actions) ? result.recommended_actions : [];

  return (
    <div className="w-full space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* ── Top row: gauge + verdict + badges ─────────────────────────────── */}
      <div className={`rounded-2xl border p-6 ${colors.bg} flex flex-col sm:flex-row items-center gap-6`}>

        {/* Gauge */}
        <div className="shrink-0">
          <CircularGauge score={result.risk_score} />
        </div>

        {/* Verdict + meta */}
        <div className="flex-1 space-y-4 text-center sm:text-left">
          <span className={`inline-block px-4 py-1.5 rounded-full text-sm font-semibold border ${verdict.className}`}>
            {verdict.label}
          </span>

          <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
            {/* Category pill */}
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300">
              🏷 {slugToLabel(result.category)}
            </span>
            {/* Confidence pill */}
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300">
              🎯 {confidencePct}% confidence
            </span>
            {/* Model pill */}
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700 text-slate-400">
              ⚡ {(result.processing_time_ms ?? 0).toFixed(0)} ms
            </span>
          </div>
        </div>
      </div>

      {/* ── Manipulation tactics ──────────────────────────────────────────── */}
      {tactics.length > 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Manipulation Tactics Detected
          </h3>
          <ChipArray
            items={tactics}
            colorClass="bg-red-500/10 text-red-300 border-red-500/30"
          />
        </section>
      )}

      {/* ── Red flags ─────────────────────────────────────────────────────── */}
      {flags.length > 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Red Flags Found
          </h3>
          <ul className="space-y-2">
            {flags.map((flag, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300 leading-relaxed">
                <span className="text-red-400 mt-0.5 shrink-0">▸</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Explanation callout ───────────────────────────────────────────── */}
      <section className="rounded-xl border border-slate-700 bg-slate-900 p-5 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Analysis
        </h3>
        <p className="text-sm text-slate-200 leading-relaxed">{result.explanation || "No details available."}</p>
        {result.explanation_hi && (
          <p className="text-sm text-slate-400 leading-relaxed border-t border-slate-800 pt-3">
            {result.explanation_hi}
          </p>
        )}
      </section>

      {/* ── Recommended actions ───────────────────────────────────────────── */}
      {actions.length > 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            What You Should Do Now
          </h3>
          <ol className="space-y-2">
            {actions.map((action, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300 leading-relaxed">
                <span className="shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-slate-800 text-slate-500 text-xs font-bold">
                  {i + 1}
                </span>
                <span>{action}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ── Action buttons ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3 pt-1">
        <a
          href="tel:1930"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 active:bg-red-700 text-white text-sm font-semibold transition-colors"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 011 1V20a1 1 0 01-1 1C10.01 21 3 13.99 3 5a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.45.57 3.57a1 1 0 01-.25 1.02l-2.2 2.2z"/>
          </svg>
          Call 1930 Helpline
        </a>

        <a
          href="https://cybercrime.gov.in"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:bg-slate-900 border border-slate-700 text-slate-200 text-sm font-semibold transition-colors"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
          </svg>
          File Report Online
        </a>
      </div>
    </div>
  );
}
