// =============================================================================
// frontend/src/pages/ProductionSchedule/DayOutOfDays.tsx
// Renders the DOOD grid (cast × shoot days) as an HTML table and offers
// CSV / PDF download buttons. Light theme, blue-500 accents.
//
// Cell colour palette matches the Phase 6 PDF exporter:
//   W / SW / WF / SWF → emerald (working)
//   H                 → amber   (hold)
//   S / F / T         → blue    (start/finish/travel)
// =============================================================================

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  Users,
} from "lucide-react";

import {
  downloadDood,
  getDood,
  getStripboard,
  triggerDownload,
  type DoodGrid,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

const CELL_TONE: Record<string, string> = {
  W:   "bg-emerald-50 text-emerald-700 border-emerald-100",
  SW:  "bg-emerald-50 text-emerald-700 border-emerald-100",
  WF:  "bg-emerald-50 text-emerald-700 border-emerald-100",
  SWF: "bg-emerald-50 text-emerald-700 border-emerald-100",
  H:   "bg-amber-50 text-amber-700 border-amber-100",
  S:   "bg-blue-50 text-blue-700 border-blue-100",
  F:   "bg-blue-50 text-blue-700 border-blue-100",
  T:   "bg-blue-50 text-blue-700 border-blue-100",
};

interface ColumnSpec {
  dayNumber: number;
  date: string | null;
}

export default function DayOutOfDays({ productionId }: Props) {
  const [grid, setGrid] = useState<DoodGrid>({});
  const [columns, setColumns] = useState<ColumnSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"csv" | "pdf" | null>(null);

  useEffect(() => {
    if (!productionId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getDood(productionId), getStripboard(productionId)])
      .then(([doodGrid, stripboard]) => {
        if (cancelled) return;
        setGrid(doodGrid);

        // Day numbers come from the grid keys (string-encoded ints).
        // Dates come from the stripboard's bucket so the header reads
        // "Day 1 (2026-01-15)" same as the CSV exporter.
        const numbers = new Set<number>();
        Object.values(doodGrid).forEach((row) => {
          Object.keys(row).forEach((k) => numbers.add(Number(k)));
        });
        // Fall back to whatever's in the stripboard if the grid is empty.
        // day_number → date lookup from the stripboard's scheduled days.
        const dateByDay = new Map<number, string | null>();
        stripboard.days.forEach((d) => {
          numbers.add(d.day_number);
          dateByDay.set(d.day_number, d.date);
        });

        const cols = Array.from(numbers)
          .filter((n) => !Number.isNaN(n))
          .sort((a, b) => a - b)
          .map<ColumnSpec>((n) => ({
            dayNumber: n,
            date: dateByDay.get(n) ?? null,
          }));
        setColumns(cols);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? e.message
            : "Could not load Day Out of Days. Check that the backend is running.",
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

  const castIds = useMemo(() => Object.keys(grid), [grid]);

  async function handleDownload(format: "csv" | "pdf") {
    if (downloading) return;
    setDownloading(format);
    try {
      const { blob, filename } = await downloadDood(productionId, format);
      triggerDownload(blob, filename);
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : `Could not download ${format.toUpperCase()}.`,
      );
    } finally {
      setDownloading(null);
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
        <p className="text-sm">Loading Day Out of Days…</p>
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

  if (castIds.length === 0 || columns.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
        <Users className="w-10 h-10 mx-auto text-slate-300 mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">
          No DOOD data yet
        </h2>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          The Day Out of Days is derived from scenes assigned to shoot days
          and the cast appearing in each scene. Import a breakdown and build
          the stripboard to populate it.
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => handleDownload("csv")}
          disabled={downloading !== null}
          className="inline-flex items-center gap-2 px-3 py-2 bg-white text-blue-700 text-sm font-medium rounded-lg border border-blue-200 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {downloading === "csv" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileSpreadsheet className="w-4 h-4" />
          )}
          Export CSV
        </button>
        <button
          type="button"
          onClick={() => handleDownload("pdf")}
          disabled={downloading !== null}
          className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {downloading === "pdf" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileText className="w-4 h-4" />
          )}
          Export PDF
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="sticky left-0 bg-slate-50 px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider z-10">
                  Cast Member
                </th>
                {columns.map((c) => (
                  <th
                    key={c.dayNumber}
                    className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap"
                  >
                    <div>Day {c.dayNumber}</div>
                    {c.date && (
                      <div className="text-[10px] text-slate-400 font-normal mt-0.5">
                        {c.date}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {castIds.map((castId) => {
                const row = grid[castId];
                return (
                  <tr key={castId} className="hover:bg-slate-50/60 transition-colors">
                    <td className="sticky left-0 bg-white px-4 py-3 font-medium text-slate-900 whitespace-nowrap">
                      <Download className="w-3 h-3 inline-block mr-1.5 text-slate-300" />
                      {castId}
                    </td>
                    {columns.map((c) => {
                      const code = row[String(c.dayNumber)];
                      const tone = code ? (CELL_TONE[code] ?? "bg-slate-50 text-slate-600 border-slate-100") : "";
                      return (
                        <td
                          key={c.dayNumber}
                          className="px-2 py-2 text-center"
                        >
                          {code ? (
                            <span
                              className={`inline-block min-w-[40px] px-2 py-1 rounded text-xs font-semibold border ${tone}`}
                            >
                              {code}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 flex flex-wrap items-center gap-3">
          <span className="font-semibold text-slate-600">Legend:</span>
          <Legend label="SW / W / WF / SWF" toneClass={CELL_TONE.W} description="Working" />
          <Legend label="H" toneClass={CELL_TONE.H} description="Hold" />
          <Legend label="S / F / T" toneClass={CELL_TONE.S} description="Start / Finish / Travel" />
        </div>
      </div>
    </section>
  );
}

function Legend({
  label,
  toneClass,
  description,
}: {
  label: string;
  toneClass: string;
  description: string;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-block px-1.5 py-0.5 rounded border text-[10px] font-semibold ${toneClass}`}
      >
        {label}
      </span>
      <span className="text-slate-500">{description}</span>
    </span>
  );
}
