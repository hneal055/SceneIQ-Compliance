// =============================================================================
// frontend/src/pages/ProductionSchedule/CallSheetViewer.tsx
// Day-selector + per-section render of the JSON call sheet from
// GET /production-schedule/{productionId}/call-sheet/{day_number}.
// "Download PDF" button hits the sibling /pdf endpoint and triggers a
// browser download via the Blob helper.
// =============================================================================

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CalendarDays,
  Clock,
  Cloud,
  Download,
  Hospital,
  Loader2,
  MapPin,
  Users,
} from "lucide-react";

import {
  downloadCallSheetPdf,
  getCallSheetJson,
  getStripboard,
  triggerDownload,
  type CallSheetJson,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

export default function CallSheetViewer({ productionId }: Props) {
  const [availableDays, setAvailableDays] = useState<number[]>([]);
  const [dayNumber, setDayNumber] = useState<number | null>(null);
  const [callSheet, setCallSheet] = useState<CallSheetJson | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [daysLoading, setDaysLoading] = useState(true);

  // Pull the stripboard once to discover which shoot days exist.
  useEffect(() => {
    if (!productionId) return;
    let cancelled = false;
    setDaysLoading(true);
    setError(null);
    getStripboard(productionId)
      .then((data) => {
        if (cancelled) return;
        const nums = data.days
          .map((d) => d.day_number)
          .sort((a, b) => a - b);
        setAvailableDays(nums);
        if (nums.length > 0 && dayNumber === null) {
          setDayNumber(nums[0]);
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? e.message
            : "Could not load shoot days. Check that the backend is running.",
        );
      })
      .finally(() => {
        if (cancelled) return;
        setDaysLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productionId]);

  // Fetch the call sheet whenever the selected day changes.
  useEffect(() => {
    if (!productionId || dayNumber === null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setCallSheet(null);
    getCallSheetJson(productionId, dayNumber)
      .then((cs) => {
        if (cancelled) return;
        setCallSheet(cs);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? e.message
            : `Could not load call sheet for day ${dayNumber}.`,
        );
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [productionId, dayNumber]);

  async function handleDownloadPdf() {
    if (!callSheet || downloading || dayNumber === null) return;
    setDownloading(true);
    try {
      const { blob, filename } = await downloadCallSheetPdf(productionId, dayNumber);
      triggerDownload(blob, filename);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Could not download call sheet PDF.",
      );
    } finally {
      setDownloading(false);
    }
  }

  const hasScenes = useMemo(
    () => !!callSheet && callSheet.scenes && callSheet.scenes.length > 0,
    [callSheet],
  );
  const hasCrewCalls = useMemo(
    () => !!callSheet && callSheet.crew_calls && callSheet.crew_calls.length > 0,
    [callSheet],
  );

  if (daysLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
        <p className="text-sm">Loading shoot days…</p>
      </div>
    );
  }

  if (availableDays.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
        <CalendarDays className="w-10 h-10 mx-auto text-slate-300 mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">
          No shoot days available
        </h2>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Create shoot days for this production and assign scenes to them
          before generating call sheets.
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      {/* Day selector + PDF button */}
      <div className="flex flex-wrap items-end gap-3 px-4 py-3 bg-white rounded-xl border border-slate-100 shadow-sm">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="cs-day-select"
            className="text-[11px] font-semibold uppercase tracking-wider text-slate-500"
          >
            Shoot day
          </label>
          <select
            id="cs-day-select"
            value={dayNumber ?? ""}
            onChange={(e) => setDayNumber(Number(e.target.value))}
            className="min-w-[180px] px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {availableDays.map((n) => (
              <option key={n} value={n}>
                Day {n}
              </option>
            ))}
          </select>
        </div>

        <div className="ml-auto">
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={!callSheet || downloading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {downloading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Download PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
          <p className="text-sm">Loading call sheet for Day {dayNumber}…</p>
        </div>
      )}

      {callSheet && !loading && (
        <>
          {/* General call time — large blue card */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                <Clock className="w-7 h-7 text-blue-600" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  General Call
                </p>
                <p className="text-3xl font-bold text-blue-700 leading-tight mt-1">
                  {callSheet.general_call ?? "—"}
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  Day {callSheet.day_number} · {callSheet.date ?? "Date TBD"}
                </p>
              </div>
            </div>
          </div>

          {/* Logistics — location + hospital + weather */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <LogisticsCard
              icon={<MapPin className="w-5 h-5 text-blue-600" />}
              label="Location"
              value={callSheet.location}
              fallback="(no location set)"
            />
            <LogisticsCard
              icon={<Hospital className="w-5 h-5 text-blue-600" />}
              label="Nearest Hospital"
              value={callSheet.nearest_hospital}
              fallback="(no hospital on file)"
            />
            <LogisticsCard
              icon={<Cloud className="w-5 h-5 text-blue-600" />}
              label="Weather"
              value={callSheet.weather}
              fallback="(weather to be confirmed on the day)"
            />
          </div>

          {/* Scene list table */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="text-base font-semibold text-slate-900">Scenes</h3>
            </div>
            {hasScenes ? (
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-100">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Scene #</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Title</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Location</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Int/Ext</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Day/Night</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Pages</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Cast</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {callSheet.scenes.map((s, i) => (
                    <tr key={i} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-6 py-3.5 font-medium text-slate-900">
                        {s.scene_number ?? "—"}
                      </td>
                      <td className="px-6 py-3.5 text-slate-700">{s.title ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{s.location ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{s.location_type ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{s.time_of_day ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{s.page_count ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">
                        {s.cast && s.cast.length > 0 ? s.cast.join(", ") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="px-6 py-6 text-sm text-slate-500 italic">
                No scenes scheduled for this day.
              </p>
            )}
          </div>

          {/* Crew calls table */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <h3 className="text-base font-semibold text-slate-900">Crew Calls</h3>
            </div>
            {hasCrewCalls ? (
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-100">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Department</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Call Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {callSheet.crew_calls.map((c, i) => (
                    <tr key={i} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-6 py-3.5 text-slate-700">{c.department ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{c.name ?? "—"}</td>
                      <td className="px-6 py-3.5 text-slate-700">{c.call_time ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="px-6 py-6 text-sm text-slate-500 italic">
                No crew calls set for this day yet.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function LogisticsCard({
  icon,
  label,
  value,
  fallback,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | null | undefined;
  fallback: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
      <div className="flex items-start gap-3">
        <div className="shrink-0">{icon}</div>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {label}
          </p>
          <p
            className={`text-sm mt-1 ${
              value ? "text-slate-900" : "text-slate-400 italic"
            }`}
          >
            {value ?? fallback}
          </p>
        </div>
      </div>
    </div>
  );
}
