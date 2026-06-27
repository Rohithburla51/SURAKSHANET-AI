"use client";

/**
 * frontend/src/components/CounterfeitReport.tsx
 * ──────────────────────────────────────────────
 * Bank Teller — Counterfeit scan verdict + forensic metrics.
 * Zero charting libs — pure Tailwind progress bars + SVG.
 */

import React from "react";
import type { CounterfeitResult } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function verdictStyle(verdict: string): {
  bg: string; border: string; text: string; label: string; icon: string;
} {
  switch (verdict) {
    case "GENUINE":
      return {
        bg: "bg-green-500/10", border: "border-green-500/40",
        text: "text-green-300", label: "✅ GENUINE", icon: "text-green-400",
      };
    case "COUNTERFEIT":
      return {
        bg: "bg-red-500/10", border: "border-red-500/40",
        text: "text-red-300", label: "🚨 COUNTERFEIT", icon: "text-red-400",
      };
    default:
      return {
        bg: "bg-amber-500/10", border: "border-amber-500/40",
        text: "text-amber-300", label: "⚠️ SUSPECT", icon: "text-amber-400",
      };
  }
}

function barColor(value: number, thresholdHigh = 0.75, thresholdLow = 0.5): string {
  if (value >= thresholdHigh) return "bg-green-500";
  if (value >= thresholdLow)  return "bg-amber-500";
  return "bg-red-500";
}

function slugToLabel(slug: string): string {
  return slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─────────────────────────────────────────────────────────────────────────────
// Progress bar row
// ─────────────────────────────────────────────────────────────────────────────

interface MetricBarProps {
  label: string;
  value: number;      // 0.0–1.0 scale (except laplacian which needs manual normalization)
  suffix?: string;
  thresholdHigh?: number;
  thresholdLow?: number;
}

function MetricBar({ label, value, suffix, thresholdHigh = 0.75, thresholdLow = 0.5 }: MetricBarProps) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = barColor(value, thresholdHigh, thresholdLow);

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400 font-medium">{label}</span>
        <span className="text-slate-300 font-mono">{suffix ?? `${pct.toFixed(0)}%`}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  result: CounterfeitResult;
}

export default function CounterfeitReport({ result }: Props) {
  const v = verdictStyle(result.verdict);
  const m = result.opencv_metrics;

  // Normalize laplacian_variance to 0–1 for display (cap at 500 as "maximum expected")
  const lapNormalized = Math.min(1, m.laplacian_variance / 500);
  // Normalize bleed_line_count to 0–1 (cap at 16 as genuine baseline)
  const bleedNormalized = Math.min(1, m.bleed_line_count / 16);

  return (
    <div className="w-full space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* ── Verdict Banner ────────────────────────────────────────────────── */}
      <div className={`rounded-2xl border ${v.border} ${v.bg} p-6 flex flex-col items-center gap-3`}>
        <span className={`text-4xl sm:text-5xl font-black tracking-tight ${v.text}`}>
          {v.label}
        </span>
        <div className="flex flex-wrap justify-center gap-3 mt-1">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">
            Score: {result.final_score}/100
          </span>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">
            Confidence: {(result.confidence * 100).toFixed(0)}%
          </span>
          {result.denomination > 0 && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">
              ₹{result.denomination}
            </span>
          )}
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700 text-slate-500">
            ⚡ {result.processing_time_ms.toFixed(0)} ms
          </span>
        </div>
      </div>

      {/* ── Forensics Breakdown ───────────────────────────────────────────── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Forensic Metrics
        </h3>

        <MetricBar
          label="FFT Watermark Opacity"
          value={m.fft_watermark_opacity}
          suffix={`${(m.fft_watermark_opacity * 100).toFixed(1)}%`}
        />
        <MetricBar
          label="CLAHE Contrast Score"
          value={m.clahe_contrast_score}
          suffix={`${(m.clahe_contrast_score * 100).toFixed(1)}%`}
        />
        <MetricBar
          label="Intaglio Print Sharpness"
          value={lapNormalized}
          suffix={m.laplacian_variance.toFixed(1)}
          thresholdHigh={0.30}
          thresholdLow={0.12}
        />
        <MetricBar
          label="Sobel Edge Density"
          value={m.sobel_edge_density}
          suffix={`${(m.sobel_edge_density * 100).toFixed(1)}%`}
          thresholdHigh={0.50}
          thresholdLow={0.30}
        />
        <MetricBar
          label="Bleed Line Count"
          value={bleedNormalized}
          suffix={`${m.bleed_line_count} lines`}
          thresholdHigh={0.625}
          thresholdLow={0.5}
        />
      </section>

      {/* ── Features Passed / Failed ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Passed */}
        {result.features_passed.length > 0 && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-green-500/80">
              ✓ Features Passed
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.features_passed.map((f) => (
                <span
                  key={f}
                  className="px-3 py-1 rounded-full text-xs font-medium border bg-green-500/10 text-green-300 border-green-500/30"
                >
                  {slugToLabel(f)}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Failed */}
        {result.features_failed.length > 0 && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-red-500/80">
              ✗ Features Failed
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.features_failed.map((f) => (
                <span
                  key={f}
                  className="px-3 py-1 rounded-full text-xs font-medium border bg-red-500/10 text-red-300 border-red-500/30"
                >
                  {slugToLabel(f)}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* ── AI Explanation Callout ─────────────────────────────────────────── */}
      <section className="rounded-xl border border-slate-700 bg-slate-900 p-5 space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          AI Assessment
        </h3>
        <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
          {result.explanation}
        </p>
      </section>

      {/* ── Recommended Actions ───────────────────────────────────────────── */}
      {result.recommended_actions.length > 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Teller Actions
          </h3>
          <ol className="space-y-2">
            {result.recommended_actions.map((action, i) => (
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
    </div>
  );
}
