"use client";

/**
 * frontend/src/components/NetworkGraph.tsx
 * ─────────────────────────────────────────
 * SurakshaNet AI — Phase 5: vis-network graph renderer
 * Model: Claude Sonnet 4.6 (1.3x) — canvas rendering logic
 *
 * Reads vis-network from window (CDN injected in layout.tsx).
 * Transforms our NetworkQueryResult into vis.DataSets,
 * applies high-contrast node colours by label, and configures
 * barnesHut physics for non-overlapping layout.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import type { GraphNode, GraphEdge, NetworkQueryResult } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// vis-network type shim (loaded from CDN at runtime)
// ─────────────────────────────────────────────────────────────────────────────

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window {
    vis?: {
      DataSet: new (data: any[]) => any;
      Network: new (container: HTMLElement, data: any, options: any) => any;
    };
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// ─────────────────────────────────────────────────────────────────────────────
// Node colour schema — high contrast on dark background
// ─────────────────────────────────────────────────────────────────────────────

interface NodeStyle {
  background: string;
  border: string;
  fontColor: string;
  shape: string;
}

const NODE_STYLES: Record<string, NodeStyle> = {
  FraudActor:  { background: "#dc2626", border: "#991b1b", fontColor: "#fef2f2", shape: "dot"     },
  Syndicate:   { background: "#9333ea", border: "#6b21a8", fontColor: "#f5f3ff", shape: "diamond" },
  PhoneNumber: { background: "#475569", border: "#334155", fontColor: "#f1f5f9", shape: "dot"     },
  BankAccount: { background: "#d97706", border: "#92400e", fontColor: "#fffbeb", shape: "box"     },
  UPIId:       { background: "#0891b2", border: "#155e75", fontColor: "#ecfeff", shape: "dot"     },
  Victim:      { background: "#059669", border: "#065f46", fontColor: "#ecfdf5", shape: "triangle"},
};

const DEFAULT_STYLE: NodeStyle = {
  background: "#64748b", border: "#475569", fontColor: "#f8fafc", shape: "dot",
};

function getNodeStyle(label: string): NodeStyle {
  return NODE_STYLES[label] ?? DEFAULT_STYLE;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers — transform API payloads → vis DataSet format
// ─────────────────────────────────────────────────────────────────────────────

function buildVisNodes(nodes: GraphNode[]) {
  return nodes.map((n) => {
    const style = getNodeStyle(n.label);
    // Pick the best display name from properties
    const displayName =
      (n.properties.name as string) ||
      (n.properties.number as string) ||
      (n.properties.account_id as string) ||
      (n.properties.upi_id as string) ||
      (n.properties.case_id as string) ||
      n.label;

    return {
      id:    n.id,
      label: displayName,
      group: n.label,
      title: `[${n.label}] ${displayName}`,
      shape: style.shape,
      color: {
        background: style.background,
        border:     style.border,
        highlight:  { background: style.border, border: style.fontColor },
      },
      font: {
        color: style.fontColor,
        size:  12,
        face:  "system-ui, sans-serif",
      },
      size: n.label === "FraudActor" ? 24 : n.label === "Syndicate" ? 28 : 18,
      borderWidth: 2,
    };
  });
}

function buildVisEdges(edges: GraphEdge[]) {
  return edges.map((e, i) => ({
    id:     `edge-${i}`,
    from:   e.source,
    to:     e.target,
    label:  e.label,
    arrows: "to",
    color:  { color: "#475569", highlight: "#94a3b8" },
    font:   { color: "#64748b", size: 10, strokeWidth: 0, align: "middle" },
    width:  1.5,
    smooth: { type: "curvedCW", roundness: 0.15 },
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// vis-network options — barnesHut physics with slight repulsion
// ─────────────────────────────────────────────────────────────────────────────

const NETWORK_OPTIONS = {
  physics: {
    enabled: true,
    solver: "barnesHut",
    barnesHut: {
      gravitationalConstant: -4000,
      centralGravity:        0.2,
      springLength:          140,
      springConstant:        0.04,
      damping:               0.09,
      avoidOverlap:          0.6,
    },
    stabilization: {
      iterations: 150,
      updateInterval: 25,
    },
  },
  interaction: {
    hover:           true,
    tooltipDelay:    120,
    zoomView:        true,
    dragNodes:       true,
    multiselect:     true,
    navigationButtons: false,
    keyboard:        true,
  },
  edges: {
    smooth: { type: "curvedCW", roundness: 0.15 },
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
  },
  nodes: {
    borderWidth: 2,
    shadow:      { enabled: true, color: "rgba(0,0,0,0.5)", size: 8 },
  },
  layout: {
    improvedLayout: true,
    randomSeed: 42,
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

interface NetworkGraphProps {
  result: NetworkQueryResult;
}

export default function NetworkGraph({ result }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const networkRef   = useRef<any>(null);
  const [ready, setReady]     = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // ── Initialise / update vis-network ─────────────────────────────────────
  useEffect(() => {
    const vis = window.vis;
    if (!vis) {
      setError("vis-network library not loaded. Check CDN injection in layout.tsx.");
      return;
    }
    if (!containerRef.current) return;
    if (result.nodes.length === 0) {
      // Destroy existing network if we get an empty result
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
      setReady(false);
      return;
    }

    // Build datasets
    const visNodes = new vis.DataSet(buildVisNodes(result.nodes));
    const visEdges = new vis.DataSet(buildVisEdges(result.edges));

    // Destroy previous instance
    if (networkRef.current) {
      networkRef.current.destroy();
    }

    // Create
    const network = new vis.Network(
      containerRef.current,
      { nodes: visNodes, edges: visEdges },
      NETWORK_OPTIONS,
    );
    networkRef.current = network;
    setReady(false);

    // Mark ready once physics stabilise
    network.once("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      setReady(true);
    });

    // Timeout fallback — force render even if stabilisation stalls
    const timeout = setTimeout(() => {
      if (!ready) {
        network.setOptions({ physics: { enabled: false } });
        setReady(true);
      }
    }, 4000);

    return () => {
      clearTimeout(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  // ── Fit to viewport after ready ────────────────────────────────────────
  useEffect(() => {
    if (ready && networkRef.current) {
      networkRef.current.fit({ animation: { duration: 400, easingFunction: "easeOutQuad" } });
    }
  }, [ready]);

  // ── Cleanup on unmount ─────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, []);

  // ── Legend ─────────────────────────────────────────────────────────────────
  const Legend = useCallback(() => (
    <div className="flex flex-wrap gap-3">
      {Object.entries(NODE_STYLES).map(([label, style]) => (
        <div key={label} className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-full border"
            style={{ backgroundColor: style.background, borderColor: style.border }}
          />
          <span className="text-xs text-slate-400">{label}</span>
        </div>
      ))}
    </div>
  ), []);

  return (
    <div className="w-full space-y-4 animate-in fade-in duration-300">
      {/* ── Graph canvas container ───────────────────────────────────────── */}
      <div className="relative rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
        {/* Loading overlay */}
        {!ready && result.nodes.length > 0 && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Computing graph layout…
            </div>
          </div>
        )}

        {/* vis-network canvas target */}
        <div
          ref={containerRef}
          className="w-full"
          style={{ height: "480px" }}
        />

        {/* Empty state */}
        {result.nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <svg className="w-10 h-10 text-slate-800" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
            <p className="text-xs text-slate-700 max-w-xs text-center">
              {result.summary || "No graph data. Submit a query above."}
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80 p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* ── Legend ────────────────────────────────────────────────────────── */}
      <Legend />

      {/* ── Summary + Cypher callout ─────────────────────────────────────── */}
      {(result.summary || result.cypher_query) && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-5 space-y-3">
          {result.summary && (
            <div className="space-y-1">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                Intelligence Summary
              </h4>
              <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                {result.summary}
              </p>
            </div>
          )}
          {result.cypher_query && (
            <div className="space-y-1 pt-2 border-t border-slate-800">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                Generated Cypher
              </h4>
              <pre className="text-xs text-indigo-300 bg-slate-800/60 rounded-lg px-3 py-2 overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">
                {result.cypher_query}
              </pre>
            </div>
          )}
          {/* Query metadata */}
          <div className="flex flex-wrap gap-2 pt-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
              {result.row_count} rows
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
              {result.nodes.length} nodes
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
              {result.edges.length} edges
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
              ⚡ {result.processing_time_ms.toFixed(0)} ms
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
