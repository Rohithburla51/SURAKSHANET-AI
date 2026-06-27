"use client";

/**
 * frontend/src/components/BankPortal.tsx
 * ─────────────────────────────────────────
 * SurakshaNet AI — Bank Teller Counterfeit Detection Portal (component)
 * Extracted from app/bank/page.tsx for unified tab layout.
 */

import React, { useCallback, useRef, useState } from "react";
import { scanNote, type CounterfeitResult } from "@/lib/api";
import CounterfeitReport from "@/components/CounterfeitReport";

const MAX_IMAGE_BYTES = 15 * 1024 * 1024;
const ALLOWED_TYPES   = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp", "image/tiff"]);
const DENOMINATIONS   = [100, 200, 500, 2000] as const;

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export default function BankPortal() {
  const [imageFile,    setImageFile]    = useState<File | null>(null);
  const [previewUrl,   setPreviewUrl]   = useState<string | null>(null);
  const [denomination, setDenomination] = useState<number>(500);
  const [loading,      setLoading]      = useState(false);
  const [result,       setResult]       = useState<CounterfeitResult | null>(null);
  const [error,        setError]        = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const clearImage = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImageFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [previewUrl]);

  const handleFileSelect = useCallback((file: File | null) => {
    setResult(null);
    setError(null);
    if (!file) { clearImage(); return; }
    if (!ALLOWED_TYPES.has(file.type)) {
      setError(`Invalid type "${file.type}". Accepted: JPEG, PNG, WEBP, BMP, TIFF.`);
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError(`Too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 15 MB.`);
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImageFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }, [clearImage, previewUrl]);

  const onInputChange  = useCallback((e: React.ChangeEvent<HTMLInputElement>) => handleFileSelect(e.target.files?.[0] ?? null), [handleFileSelect]);
  const onDrop         = useCallback((e: React.DragEvent) => { e.preventDefault(); handleFileSelect(e.dataTransfer.files?.[0] ?? null); }, [handleFileSelect]);
  const onDragOver     = useCallback((e: React.DragEvent) => e.preventDefault(), []);

  const handleSubmit = useCallback(async () => {
    if (!imageFile) { setError("Please upload a note image first."); return; }
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      setResult(await scanNote(imageFile, denomination));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }, [imageFile, denomination]);

  const handleDemoClick = useCallback(async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 100; canvas.height = 60;
    const ctx = canvas.getContext("2d");
    if (ctx) { ctx.fillStyle = "#1e293b"; ctx.fillRect(0, 0, 100, 60); ctx.fillStyle = "#94a3b8"; ctx.font = "14px sans-serif"; ctx.textAlign = "center"; ctx.fillText("DEMO", 50, 35); }
    const blob     = await new Promise<Blob>((res) => canvas.toBlob((b) => res(b!), "image/png"));
    const demoFile = new File([blob], "demo-note.png", { type: "image/png" });
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImageFile(demoFile);
    setPreviewUrl(URL.createObjectURL(demoFile));
    setDenomination(500);
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      setResult(await scanNote(demoFile, 500));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Demo request failed.");
    } finally {
      setLoading(false);
    }
  }, [previewUrl]);

  const canSubmit = !loading && imageFile !== null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="space-y-1.5">
        <h2 className="text-xl font-bold tracking-tight">Bank Teller Portal</h2>
        <p className="text-sm text-slate-400 max-w-lg leading-relaxed">
          Upload a photo of a currency note. Our AI runs forensic FFT watermark analysis,
          intaglio sharpness detection, and LLaVA vision verification in under 3 seconds.
        </p>
      </header>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

        {/* LEFT: Input */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-5">
          {/* Dropzone */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Note Image</label>
            <div
              onDrop={onDrop}
              onDragOver={onDragOver}
              onClick={() => fileInputRef.current?.click()}
              className={`relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
                cursor-pointer transition-colors min-h-[200px] overflow-hidden
                ${imageFile ? "border-indigo-500/50 bg-indigo-500/5" : "border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/60"}`}
              role="button"
              aria-label="Click or drag to upload note image"
            >
              {previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={previewUrl} alt="Note preview" className="max-h-52 max-w-full object-contain rounded-lg" />
              ) : (
                <>
                  <svg className="w-8 h-8 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
                  </svg>
                  <span className="text-xs text-slate-500 text-center px-4">
                    Click or drag & drop<br />JPEG, PNG, WEBP · Max 15 MB
                  </span>
                </>
              )}
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff" onChange={onInputChange} disabled={loading} className="sr-only" />
            </div>
            {imageFile && (
              <div className="flex items-center justify-between text-xs text-slate-500 mt-1">
                <span className="truncate max-w-[200px]">{imageFile.name}</span>
                <button type="button" onClick={clearImage} className="text-slate-500 hover:text-red-400 transition-colors">Remove</button>
              </div>
            )}
          </div>

          {/* Denomination */}
          <div className="space-y-1.5">
            <label htmlFor="bank-denomination" className="text-xs font-medium text-slate-400 uppercase tracking-wider">Denomination</label>
            <select
              id="bank-denomination"
              value={denomination}
              onChange={(e) => setDenomination(Number(e.target.value))}
              disabled={loading}
              className="w-full rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-sm px-4 py-2.5
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500 transition-colors appearance-none"
            >
              {DENOMINATIONS.map((d) => <option key={d} value={d}>₹{d}</option>)}
            </select>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="flex flex-wrap gap-3 pt-1">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500
                         active:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed
                         text-white text-sm font-semibold transition-colors"
            >
              {loading ? <><Spinner />Scanning…</> : (
                <>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  Verify Note
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleDemoClick}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60
                         hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed
                         text-slate-300 text-sm font-medium transition-colors"
            >
              Load Demo Suspect Note
            </button>
          </div>
        </div>

        {/* RIGHT: Report */}
        <div className="min-h-[200px]">
          {result ? (
            <CounterfeitReport result={result} />
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-8 flex flex-col items-center justify-center gap-3 min-h-[300px]">
              <svg className="w-12 h-12 text-slate-800" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                <path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm0 2v12h16V6H4zm2 2h2v2H6V8zm10 0h2v2h-2V8zm-5 2a3 3 0 110 6 3 3 0 010-6z" />
              </svg>
              <p className="text-sm text-slate-700 text-center max-w-xs">
                Upload a note image or click "Load Demo Suspect Note" to see the forensic report.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center text-xs text-slate-700 pt-2 pb-1 space-y-1">
        <p>For RBI reporting visit <a href="https://www.rbi.org.in/counterfeit" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-slate-400 underline">rbi.org.in</a> · Results are advisory only.</p>
      </footer>
    </div>
  );
}
