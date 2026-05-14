// =============================================================================
// frontend/src/pages/ProductionSchedule/index.tsx
// Top-level Production Schedule page. Hosts:
//   1. Page header banner (title + production selector)
//   2. Five-tab sub-navigation (Import / Stripboard / DOOD / Call Sheets / Jurisdiction)
//   3. The active sub-tab's component, threaded with the chosen production_id
//
// Light-theme shell mirrors ProductionDetail.tsx — no gold, no dark gradient.
// =============================================================================

import { useEffect, useState } from "react";
import {
  Calendar,
  CalendarRange,
  ClipboardCheck,
  FileSpreadsheet,
  FileText,
  ListChecks,
  Upload,
} from "lucide-react";

import { api } from "../../api";
import type { Production } from "../../types";

import ImportPanel from "./ImportPanel";
import Stripboard from "./Stripboard";
import DayOutOfDays from "./DayOutOfDays";
import CallSheetViewer from "./CallSheetViewer";
import JurisdictionTracker from "./JurisdictionTracker";

type TabId =
  | "import"
  | "stripboard"
  | "dood"
  | "callSheet"
  | "jurisdiction";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "import",       label: "Import",                icon: <Upload className="w-3.5 h-3.5" /> },
  { id: "stripboard",   label: "Stripboard",            icon: <ListChecks className="w-3.5 h-3.5" /> },
  { id: "dood",         label: "Day Out of Days",       icon: <FileSpreadsheet className="w-3.5 h-3.5" /> },
  { id: "callSheet",    label: "Call Sheets",           icon: <FileText className="w-3.5 h-3.5" /> },
  { id: "jurisdiction", label: "Jurisdiction Tracker",  icon: <ClipboardCheck className="w-3.5 h-3.5" /> },
];

export default function ProductionSchedule() {
  const [productions, setProductions] = useState<Production[]>([]);
  const [productionId, setProductionId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<TabId>("import");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load the production list on mount and default to the first one.
  // Same fetch pattern used elsewhere in the app (Productions page).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.productions
      .list()
      .then((list) => {
        if (cancelled) return;
        setProductions(list);
        if (list.length > 0) setProductionId(list[0].id);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? e.message
            : "Could not load productions. Make sure the backend is running.",
        );
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="-m-8 min-h-screen">
      {/* Header banner — same shape as ProductionDetail.tsx:230-262 */}
      <div className="bg-white border-b border-slate-200 px-8 py-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
            <CalendarRange className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-slate-900">Production Schedule</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Import script breakdowns, build the stripboard, generate call
              sheets, and push verified shoot-day counts to the Incentive
              Calculator.
            </p>
          </div>

          {/* Production selector */}
          <div className="flex flex-col items-end gap-1">
            <label
              htmlFor="ps-production-select"
              className="text-[11px] font-semibold uppercase tracking-wider text-slate-500"
            >
              Production
            </label>
            <select
              id="ps-production-select"
              value={productionId}
              onChange={(e) => setProductionId(e.target.value)}
              disabled={loading || productions.length === 0}
              className="min-w-[260px] px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 disabled:text-slate-500"
            >
              {loading && <option value="">Loading…</option>}
              {!loading && productions.length === 0 && (
                <option value="">(no productions found)</option>
              )}
              {productions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Sub-nav tab strip — mirrors ProductionDetail.tsx:264-275 */}
      <div className="bg-white border-b border-slate-200 px-8">
        <div className="flex gap-1">
          {TABS.map((t) => {
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-4 py-3.5 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content area */}
      <div className="p-8 max-w-7xl mx-auto">
        {error && (
          <div className="mb-6 p-4 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
            <Calendar className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!productionId && !loading ? (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
            <CalendarRange className="w-10 h-10 mx-auto text-slate-300 mb-3" />
            <h2 className="text-lg font-semibold text-slate-900">
              No production selected
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Create a production first, then return here to schedule it.
            </p>
          </div>
        ) : null}

        {productionId && activeTab === "import" && (
          <ImportPanel productionId={productionId} />
        )}
        {productionId && activeTab === "stripboard" && (
          <Stripboard productionId={productionId} />
        )}
        {productionId && activeTab === "dood" && (
          <DayOutOfDays productionId={productionId} />
        )}
        {productionId && activeTab === "callSheet" && (
          <CallSheetViewer productionId={productionId} />
        )}
        {productionId && activeTab === "jurisdiction" && (
          <JurisdictionTracker productionId={productionId} />
        )}
      </div>
    </div>
  );
}
