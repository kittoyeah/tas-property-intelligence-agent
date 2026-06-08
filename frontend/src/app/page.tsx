"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Mode   = "buyer" | "construction" | "da_owner";
type Intent = "just_checking" | "granny_flat" | "extension" | "additional_storey" | "new_dwelling" | "outbuilding";

const MODE_LABELS: Record<Mode, string> = {
  buyer:        "Buyer / Investor",
  construction: "Tradie / Builder",
  da_owner:     "DA Owner / Developer",
};

const INTENT_LABELS: Record<Intent, string> = {
  just_checking:     "Just checking",
  granny_flat:       "Granny flat / secondary dwelling",
  extension:         "Extension / renovation",
  additional_storey: "Additional storey",
  new_dwelling:      "New dwelling",
  outbuilding:       "Outbuilding / shed / garage",
};

interface Overlay {
  code?: string;
  name?: string;
  lps_ref?: string;
}

interface CheckResult {
  address:       string;
  mode:          Mode;
  intent:        Intent;
  council?:      { name: string };
  zone?:         { zone: string; zone_abb?: string };
  overlays:      Overlay[];
  response:      string;
  error?:        string;
}

export default function Home() {
  const [address, setAddress]   = useState("");
  const [mode, setMode]         = useState<Mode>("buyer");
  const [intent, setIntent]     = useState<Intent>("just_checking");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<CheckResult | null>(null);
  const [error, setError]       = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, mode, intent }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(detail.detail ?? `HTTP ${res.status}`);
      }

      const data: CheckResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">SC</div>
          <div>
            <h1 className="text-lg font-semibold text-slate-900">SiteCheck</h1>
            <p className="text-xs text-slate-500">Tasmania Property Intelligence · Hobart LPS 2025</p>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-6">

        {/* Input form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 space-y-5 shadow-sm">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Property address</label>
            <input
              type="text"
              required
              value={address}
              onChange={e => setAddress(e.target.value)}
              placeholder="e.g. 8 Nelson Road Sandy Bay TAS 7005"
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">I am a…</label>
              <select
                value={mode}
                onChange={e => setMode(e.target.value as Mode)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {(Object.entries(MODE_LABELS) as [Mode, string][]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">I want to…</label>
              <select
                value={intent}
                onChange={e => setIntent(e.target.value as Intent)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {(Object.entries(INTENT_LABELS) as [Intent, string][]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !address.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors"
          >
            {loading ? "Checking…" : "Check this site"}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Meta strip */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex flex-wrap gap-2 text-xs">
                {result.council && (
                  <span className="bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full font-medium">
                    {result.council.name} Council
                  </span>
                )}
                {result.zone && (
                  <span className="bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">
                    Zone: {result.zone.zone_abb ?? result.zone.zone}
                  </span>
                )}
                {result.overlays?.length > 0 ? (
                  result.overlays.map((o, i) => (
                    <span key={i} className="bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full font-medium">
                      {o.name ?? o.code}
                    </span>
                  ))
                ) : (
                  <span className="bg-green-50 text-green-700 px-2.5 py-1 rounded-full font-medium">No overlays</span>
                )}
              </div>
            </div>

            {/* Agent response */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">SC</div>
                <span className="text-sm font-medium text-slate-700">SiteCheck Analysis</span>
              </div>
              <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap leading-relaxed">
                {result.response}
              </div>
            </div>

            {/* Disclaimer */}
            <p className="text-xs text-slate-400 text-center px-4">
              This tool provides planning information only. It is not legal, engineering, or financial advice.
              Always verify with your council and consult a licensed professional before commencing works.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
