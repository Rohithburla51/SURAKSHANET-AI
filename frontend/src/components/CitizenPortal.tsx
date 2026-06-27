"use client";

/**
 * frontend/src/components/CitizenPortal.tsx
 * ────────────────────────────────────────────
 * SurakshaNet AI — Citizen Safety Portal (component)
 * Extracted from app/citizen/page.tsx for unified tab layout.
 */

import React, { useCallback, useRef, useState } from "react";
import { analyzeScam, analyzeScamAudio, type ScamAnalysisResult } from "@/lib/api";
import RiskScore from "@/components/RiskScore";

const DEMO_MESSAGE = `[URGENT] आपका Aadhaar Card एक money laundering case में use हुआ है।
CBI Officer Rajesh Kumar (Badge: CBI/DL/2847) speaking.

Your Aadhaar number XXXX-XXXX-8421 has been found linked to 14 suspicious bank accounts used for narcotics trafficking across 4 states.

आपको अभी 2 घंटे के अंदर ₹85,000 "RBI Verification Account" में transfer करना होगा — otherwise आपकी immediate arrest होगी।

DO NOT tell your family or bank. This is a classified Central Bureau of Investigation operation. Stay on this video call.

Call back: +91-98765-43210 (CBI Helpdesk)`;

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function AudioFileLabel({ file, onClear }: { file: File | null; onClear: () => void }) {
  if (!file) return null;
  const sizeKb = (file.size / 1024).toFixed(1);
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 mt-2">
      <svg className="w-3.5 h-3.5 text-indigo-400 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M12 3v10.55A4 4 0 1014 17V7h4V3h-6z" />
      </svg>
      <span className="truncate flex-1">{file.name}</span>
      <span className="shrink-0 text-slate-500">{sizeKb} KB</span>
      <button type="button" onClick={onClear} className="shrink-0 text-slate-500 hover:text-red-400 transition-colors" aria-label="Remove audio file">✕</button>
    </div>
  );
}

type InputMode = "text" | "audio";

export default function CitizenPortal() {
  const [mode,      setMode]      = useState<InputMode>("text");
  const [text,      setText]      = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<ScamAnalysisResult | null>(null);
  const [error,     setError]     = useState<string | null>(null);

  const audioInputRef = useRef<HTMLInputElement>(null);
  const resultRef     = useRef<HTMLDivElement>(null);

  const handleDemoFill = useCallback(() => {
    setMode("text");
    setText(DEMO_MESSAGE);
    setResult(null);
    setError(null);
  }, []);

  const handleAudioChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setAudioFile(e.target.files?.[0] ?? null);
    setResult(null);
    setError(null);
  }, []);

  const handleClearAudio = useCallback(() => {
    setAudioFile(null);
    if (audioInputRef.current) audioInputRef.current.value = "";
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    const hasText  = text.trim().length > 0;
    const hasAudio = mode === "audio" && audioFile !== null;
    if (!hasText && !hasAudio) {
      setError("Please paste a suspicious message or upload an audio recording.");
      return;
    }

    setLoading(true);
    try {
      const data = hasAudio ? await analyzeScamAudio(audioFile!) : await analyzeScam(text.trim());
      const safeResult: ScamAnalysisResult = {
        risk_score:           data.risk_score ?? 0,
        category:             data.category ?? "unknown",
        confidence:           data.confidence ?? 0,
        verdict:              data.verdict ?? "UNCERTAIN",
        manipulation_tactics: Array.isArray(data.manipulation_tactics) ? data.manipulation_tactics : [],
        red_flags:            Array.isArray(data.red_flags) ? data.red_flags : [],
        explanation:          data.explanation || "Analysis complete.",
        explanation_hi:       data.explanation_hi || "",
        recommended_actions:  Array.isArray(data.recommended_actions) ? data.recommended_actions : [],
        rag_matches_used:     Array.isArray(data.rag_matches_used) ? data.rag_matches_used : [],
        model_used:           data.model_used || "unknown",
        processing_time_ms:   data.processing_time_ms ?? 0,
      };
      setResult(safeResult);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, [text, mode, audioFile]);

  const canSubmit = !loading && (
    (mode === "text"  && text.trim().length > 0) ||
    (mode === "audio" && audioFile !== null)
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="space-y-1.5">
        <h2 className="text-xl font-bold tracking-tight">Citizen Safety Portal</h2>
        <p className="text-sm text-slate-400 leading-relaxed max-w-lg">
          Paste a suspicious message or upload a phone-call recording. Our AI scans it against
          thousands of known Indian cybercrime patterns and gives you an instant risk verdict.
        </p>
      </header>

      {/* Input card */}
      <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-5" noValidate>
        {/* Mode toggle */}
        <div role="tablist" aria-label="Input mode" className="flex gap-1 p-1 bg-slate-800/60 rounded-xl w-fit">
          {(["text", "audio"] as InputMode[]).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => { setMode(m); setError(null); setResult(null); }}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === m ? "bg-slate-700 text-slate-100 shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {m === "text" ? "📝 Text Message" : "🎙 Audio Recording"}
            </button>
          ))}
        </div>

        {/* Text area */}
        {mode === "text" && (
          <div className="space-y-1.5">
            <label htmlFor="citizen-suspicious-text" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Paste Suspicious Message
            </label>
            <textarea
              id="citizen-suspicious-text"
              value={text}
              onChange={(e) => { setText(e.target.value); setResult(null); setError(null); }}
              placeholder="Paste an SMS, WhatsApp message, or call script here…"
              rows={7}
              maxLength={5000}
              disabled={loading}
              className="w-full rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100
                         placeholder-slate-600 text-sm px-4 py-3 resize-none
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500 transition-colors"
            />
            <div className="flex justify-end text-xs text-slate-600">
              <span>{text.length} / 5000</span>
            </div>
          </div>
        )}

        {/* Audio upload */}
        {mode === "audio" && (
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Upload Phone Call Recording
            </label>
            <label
              htmlFor="citizen-audio-upload"
              className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors h-28
                ${audioFile ? "border-indigo-500/50 bg-indigo-500/5" : "border-slate-700 bg-slate-800/40 hover:border-slate-600"}`}
            >
              <svg className="w-6 h-6 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
              </svg>
              <span className="text-xs text-slate-500">
                {audioFile ? "File selected" : "Click to upload · MP3, WAV, M4A · Max 25 MB"}
              </span>
              <input id="citizen-audio-upload" ref={audioInputRef} type="file" accept="audio/*" onChange={handleAudioChange} disabled={loading} className="sr-only" />
            </label>
            <AudioFileLabel file={audioFile} onClear={handleClearAudio} />
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-3 pt-1">
          <button
            type="submit"
            disabled={!canSubmit}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500
                       active:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed
                       text-white text-sm font-semibold transition-colors"
          >
            {loading ? <><Spinner />Analyzing…</> : (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                Analyze for Scams
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleDemoFill}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60
                       hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed
                       text-slate-300 text-sm font-medium transition-colors"
          >
            Try Demo
          </button>
        </div>
      </form>

      {/* Results */}
      {result && (
        <div ref={resultRef}>
          <RiskScore result={result} />
        </div>
      )}

      {/* Footer */}
      <footer className="text-center text-xs text-slate-700 pt-2 pb-1 space-y-1">
        <p>For emergencies call <a href="tel:1930" className="text-slate-500 hover:text-slate-400 underline">1930</a> · This tool is advisory only, not a substitute for law enforcement.</p>
      </footer>
    </div>
  );
}
