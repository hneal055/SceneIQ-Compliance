// =============================================================================
// frontend/src/pages/ProductionSchedule/Stripboard.tsx
// DAY-block + scene-strip stripboard view. Structural reference is
// SchedulePage.tsx, but the gold-and-dark visual tokens are dropped:
//   #C9973A → blue-500/600    bg-white/5 → bg-white (light shell)
//   linear-gradient page bg → inherits Layout's bg-slate-50
//   text-white/N → slate-700 / slate-500 etc.
//
// Fetches from GET /production-schedule/{productionId}/stripboard and
// maps the dict response to an ordered RenderedDay[] for rendering.
//
// Drag-and-drop reordering is NOT implemented in this phase (the
// POST /stripboard/assign endpoint exists; wiring it is a follow-up).
// =============================================================================

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Film,
  LayoutGrid,
  List,
  Loader2,
  MapPin,
  Plus,
  Users,
} from "lucide-react";

import {
  getStripboard,
  type StripboardDay,
  type StripboardSceneSnapshot,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

interface RenderedDay {
  day_number: number;
  date: string | null;
  jurisdiction: string | null;
  total_pages: number;
  scenes: StripboardSceneSnapshot[];
}

// Converts a decimal page count (`2.5`, `3.125`) to the eighths display
// used on traditional stripboards (`"2 4/8"`, `"3 1/8"`).
// Rounds to the nearest 8th to handle floating-point noise like 2.4999.
function pagesDisplay(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "0";
  const totalEighths = Math.round(value * 8);
  const full = Math.floor(totalEighths / 8);
  const rem = totalEighths % 8;
  if (rem === 0) return `${full}`;
  if (full === 0) return `${rem}/8`;
  return `${full} ${rem}/8`;
}

function formatDate(value: string | null): string {
  if (!value) return "Date TBD";
  // Treat the date as a calendar date, not a UTC instant — slicing avoids
  // off-by-one timezone display issues.
  const [y, m, d] = value.split("-");
  if (!y || !m || !d) return value;
  const dt = new Date(Number(y), Number(m) - 1, Number(d));
  return dt.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function Stripboard({ productionId }: Props) {
  const [days, setDays] = useState<RenderedDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [view, setView] = useState<"stripboard" | "list">("stripboard");

  useEffect(() => {
    if (!productionId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getStripboard(productionId)
      .then((dict) => {
        if (cancelled) return;
        const out: RenderedDay[] = Object.entries(dict)
          .map(([dn, bucket]: [string, StripboardDay]) => ({
            day_number: Number(dn),
            date: bucket.date,
            jurisdiction: bucket.jurisdiction,
            total_pages: bucket.total_pages,
            scenes: bucket.scenes,
          }))
          .sort((a, b) => a.day_number - b.day_number);
        setDays(out);
        // Expand Day 1 by default for visual context.
        if (out.length > 0) setExpanded(new Set([out[0].day_number]));
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? e.message
            : "Could not load stripboard. Check that the backend is running.",
        );
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [productionId]);

  const totals = useMemo(() => {
    let scenes = 0;
    let pages = 0;
    for (const d of days) {
      scenes += d.scenes.length;
      pages += d.total_pages || 0;
    }
    return { scenes, pages, dayCount: days.length };
  }, [days]);

  function toggleDay(n: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  }

  function expandAll() {
    setExpanded(new Set(days.map((d) => d.day_number)));
  }

  function collapseAll() {
    setExpanded(new Set());
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
        <p className="text-sm">Loading stripboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  if (days.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
        <LayoutGrid className="w-10 h-10 mx-auto text-slate-300 mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">
          No shoot days yet
        </h2>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Import a script breakdown on the Import tab, then create shoot days
          and assign scenes to populate the stripboard.
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      {/* Stats bar with view toggles */}
      <div className="flex items-center gap-4 px-4 py-3 bg-white rounded-xl border border-slate-100 shadow-sm">
        <div className="flex items-center gap-1.5">
          <Film className="w-4 h-4 text-slate-400" />
          <span className="text-xs text-slate-500">Days</span>
          <span className="text-sm font-semibold text-slate-900">{totals.dayCount}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">Scenes</span>
          <span className="text-sm font-semibold text-slate-900">{totals.scenes}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">Total pages</span>
          <span className="text-sm font-semibold text-blue-600">
            {pagesDisplay(totals.pages)}
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={expandAll}
            className="text-xs text-slate-500 hover:text-blue-600"
          >
            Expand all
          </button>
          <span className="text-slate-300">·</span>
          <button
            type="button"
            onClick={collapseAll}
            className="text-xs text-slate-500 hover:text-blue-600"
          >
            Collapse all
          </button>

          <div className="ml-4 flex items-center gap-1 p-0.5 rounded-md bg-slate-100 border border-slate-200">
            <button
              type="button"
              onClick={() => setView("stripboard")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
                view === "stripboard"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <LayoutGrid size={11} />
              Strip Board
            </button>
            <button
              type="button"
              onClick={() => setView("list")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
                view === "list"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <List size={11} />
              List
            </button>
          </div>
        </div>
      </div>

      {view === "list" ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-8 text-center text-sm text-slate-500">
          List view coming soon. Use Strip Board for now.
        </div>
      ) : (
        days.map((d) => (
          <DayBlock
            key={d.day_number}
            day={d}
            expanded={expanded.has(d.day_number)}
            onToggle={() => toggleDay(d.day_number)}
          />
        ))
      )}
    </section>
  );
}

// -----------------------------------------------------------------------------
// DayBlock — restyled version of SchedulePage's DayBlock (light theme).
// -----------------------------------------------------------------------------

interface DayBlockProps {
  day: RenderedDay;
  expanded: boolean;
  onToggle: () => void;
}

function DayBlock({ day, expanded, onToggle }: DayBlockProps) {
  const castCount = useMemo(() => {
    const names = new Set<string>();
    for (const s of day.scenes) {
      for (const c of s.cast_ids) names.add(c);
    }
    return names.size;
  }, [day.scenes]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 hover:border-blue-300 hover:bg-blue-50/30 transition-colors text-left"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-blue-500" />
        ) : (
          <ChevronRight size={14} className="text-slate-400" />
        )}

        <div className="flex flex-col items-start">
          <span className="text-[10px] font-mono text-blue-600 uppercase tracking-widest">
            Day {day.day_number}
          </span>
          <span className="text-sm font-bold text-slate-900 leading-tight">
            {formatDate(day.date)}
          </span>
        </div>

        {day.jurisdiction && (
          <div className="flex items-center gap-1 ml-2">
            <MapPin size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">{day.jurisdiction}</span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-4">
          <div className="flex items-center gap-1">
            <Clock size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">Call TBD</span>
          </div>
          <div className="flex items-center gap-1">
            <Film size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">
              {day.scenes.length} scenes
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Users size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">{castCount} cast</span>
          </div>
          <div className="px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
            <span className="text-xs font-bold text-blue-700">
              {pagesDisplay(day.total_pages)} pgs
            </span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-100 bg-slate-50/40">
          {day.scenes.length === 0 ? (
            <p className="text-sm text-slate-500 italic py-3">
              No scenes assigned to this day yet.
            </p>
          ) : (
            <div className="flex flex-col gap-1.5 mt-2">
              {day.scenes.map((s, i) => (
                <SceneStrip key={s.id ?? i} scene={s} />
              ))}
            </div>
          )}

          {/* Stub — drag-and-drop assignment hook lands in a future phase. */}
          <button
            type="button"
            disabled
            title="Drag-and-drop reordering arrives in a future phase"
            className="mt-2 flex items-center gap-2 px-3 py-2 rounded-md text-[11px] text-slate-400 border border-dashed border-slate-300 cursor-not-allowed w-full justify-center"
          >
            <Plus size={11} />
            Add scene to Day {day.day_number}
          </button>
        </div>
      )}
    </div>
  );
}

function SceneStrip({ scene }: { scene: StripboardSceneSnapshot }) {
  return (
    <div className="flex items-stretch rounded-md border border-slate-200 border-l-4 border-l-blue-400 bg-white hover:border-blue-300 transition-colors">
      {/* Scene number */}
      <div className="flex flex-col items-center justify-center px-3 py-2 min-w-[48px] border-r border-slate-100">
        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
          Sc
        </span>
        <span className="text-sm font-bold text-slate-900 leading-tight">
          {scene.scene_number}
        </span>
      </div>

      {/* Main info */}
      <div className="flex-1 px-3 py-2 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          {scene.location_type && (
            <span className="text-[10px] font-mono font-bold text-slate-500 tracking-wider">
              {scene.location_type}
            </span>
          )}
          {scene.time_of_day && (
            <span className="text-[10px] text-slate-500">{scene.time_of_day}</span>
          )}
          {scene.jurisdiction_id && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              {scene.jurisdiction_id}
            </span>
          )}
        </div>
        <p className="text-xs font-semibold text-slate-900 truncate">
          {scene.location || scene.title || "—"}
        </p>
        {scene.title && scene.location && (
          <p className="text-[11px] text-slate-500 truncate mt-0.5">{scene.title}</p>
        )}
      </div>

      {/* Cast */}
      <div className="hidden md:flex flex-col justify-center px-3 py-2 min-w-[120px] border-l border-slate-100">
        {scene.cast_ids.length === 0 ? (
          <span className="text-[10px] text-slate-400 italic">No cast</span>
        ) : (
          <>
            {scene.cast_ids.slice(0, 2).map((c) => (
              <span key={c} className="text-[10px] text-slate-600 truncate">
                {c}
              </span>
            ))}
            {scene.cast_ids.length > 2 && (
              <span className="text-[10px] text-slate-400">
                +{scene.cast_ids.length - 2} more
              </span>
            )}
          </>
        )}
      </div>

      {/* Pages */}
      <div className="flex flex-col items-center justify-center px-3 py-2 min-w-[56px] border-l border-slate-100">
        <span className="text-sm font-bold text-blue-600">
          {pagesDisplay(scene.page_count)}
        </span>
        <span className="text-[9px] text-slate-400 uppercase tracking-wider">pgs</span>
      </div>

      {/* Notes indicator */}
      {scene.notes && (
        <div
          className="flex items-center px-2 border-l border-slate-100"
          title={scene.notes}
        >
          <AlertCircle size={12} className="text-amber-500" />
        </div>
      )}
    </div>
  );
}
