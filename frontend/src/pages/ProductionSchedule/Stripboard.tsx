// =============================================================================
// frontend/src/pages/ProductionSchedule/Stripboard.tsx
// DAY-block + scene-strip stripboard view with an Unscheduled bin.
//
// Flow:
//   - GET /production-schedule/{id}/stripboard returns { days[], unscheduled }.
//   - Freshly-imported scenes land in the Unscheduled bin (no shoot day yet).
//   - "New shoot day" (POST /shoot-days) adds an empty day.
//   - Each scene strip has an "Assign ▾" dropdown (Unscheduled / Day N) that
//     calls POST /stripboard/assign or /stripboard/unassign, then refetches.
//   - Each day can be deleted (DELETE /shoot-days/{id}); its scenes return to
//     the Unscheduled bin (FK onDelete: SetNull).
//
// Visual tokens match the rest of the Production Schedule pages (blue/slate,
// light theme). Full drag-and-drop is a future enhancement; the dropdown is
// the reliable MVP affordance.
// =============================================================================

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Film,
  Inbox,
  LayoutGrid,
  Loader2,
  MapPin,
  Plus,
  Trash2,
  Users,
} from "lucide-react";

import {
  assignScene,
  createShootDay,
  deleteShootDay,
  getStripboard,
  unassignScene,
  type StripboardDay,
  type StripboardSceneSnapshot,
  type UnscheduledBin,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

// Sentinel select value for "move back to Unscheduled".
const UNSCHEDULED = "__unscheduled__";

// Converts a decimal page count (`2.5`, `3.125`) to the eighths display
// used on traditional stripboards (`"2 4/8"`, `"3 1/8"`).
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
  const [days, setDays] = useState<StripboardDay[]>([]);
  const [unscheduled, setUnscheduled] = useState<UnscheduledBin>({
    scenes: [],
    total_pages: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    const data = await getStripboard(productionId);
    setDays(data.days);
    setUnscheduled(data.unscheduled);
    return data;
  }, [productionId]);

  useEffect(() => {
    if (!productionId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    load()
      .then((data) => {
        if (cancelled) return;
        // Expand the first day by default for visual context.
        if (data.days.length > 0) {
          setExpanded(new Set([data.days[0].day_number]));
        }
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
  }, [productionId, load]);

  // Wraps a mutation: set busy, run it, refetch, surface errors.
  const mutate = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await fn();
        await load();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Action failed. Please try again.");
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const handleNewDay = () =>
    mutate(async () => {
      const created = (await createShootDay(productionId)) as { dayNumber?: number };
      if (created?.dayNumber) {
        setExpanded((prev) => new Set(prev).add(created.dayNumber as number));
      }
    });

  const handleDeleteDay = (day: StripboardDay) =>
    mutate(() => deleteShootDay(productionId, day.id));

  // Moves a scene to a target placement: a ShootDay.id, or UNSCHEDULED.
  const handleMoveScene = (sceneId: string, target: string) =>
    mutate(() =>
      target === UNSCHEDULED
        ? unassignScene(productionId, sceneId)
        : assignScene(productionId, { scene_id: sceneId, shoot_day_id: target }),
    );

  const totals = useMemo(() => {
    let scenes = unscheduled.scenes.length;
    let pages = unscheduled.total_pages || 0;
    for (const d of days) {
      scenes += d.scenes.length;
      pages += d.total_pages || 0;
    }
    return { scenes, pages, dayCount: days.length };
  }, [days, unscheduled]);

  function toggleDay(n: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
        <p className="text-sm">Loading stripboard…</p>
      </div>
    );
  }

  const isEmpty = days.length === 0 && unscheduled.scenes.length === 0;
  if (isEmpty && !error) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
        <LayoutGrid className="w-10 h-10 mx-auto text-slate-300 mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">No scenes yet</h2>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Import a script breakdown on the Import tab. Imported scenes appear
          here in the Unscheduled bin, ready to assign to shoot days.
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      {error && (
        <div className="p-4 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Stats bar + actions */}
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
          <span className="text-xs text-slate-500">Unscheduled</span>
          <span className="text-sm font-semibold text-amber-600">
            {unscheduled.scenes.length}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">Total pages</span>
          <span className="text-sm font-semibold text-blue-600">
            {pagesDisplay(totals.pages)}
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {busy && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
          <button
            type="button"
            onClick={handleNewDay}
            disabled={busy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus size={13} />
            New shoot day
          </button>
        </div>
      </div>

      {/* Unscheduled bin */}
      <UnscheduledBlock
        bin={unscheduled}
        days={days}
        busy={busy}
        onMove={handleMoveScene}
      />

      {/* Scheduled days */}
      {days.map((d) => (
        <DayBlock
          key={d.id}
          day={d}
          days={days}
          expanded={expanded.has(d.day_number)}
          busy={busy}
          onToggle={() => toggleDay(d.day_number)}
          onMove={handleMoveScene}
          onDelete={() => handleDeleteDay(d)}
        />
      ))}

      {days.length === 0 && (
        <p className="text-center text-xs text-slate-400 py-2">
          No shoot days yet — click <span className="font-semibold">New shoot day</span> to
          start scheduling, then assign scenes from the Unscheduled bin above.
        </p>
      )}
    </section>
  );
}

// -----------------------------------------------------------------------------
// Unscheduled bin
// -----------------------------------------------------------------------------

interface UnscheduledBlockProps {
  bin: UnscheduledBin;
  days: StripboardDay[];
  busy: boolean;
  onMove: (sceneId: string, target: string) => void;
}

function UnscheduledBlock({ bin, days, busy, onMove }: UnscheduledBlockProps) {
  if (bin.scenes.length === 0) return null;
  return (
    <div className="bg-amber-50/40 rounded-xl border border-amber-200 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-amber-100">
        <Inbox size={16} className="text-amber-500" />
        <div className="flex flex-col">
          <span className="text-[10px] font-mono text-amber-600 uppercase tracking-widest">
            Unscheduled
          </span>
          <span className="text-sm font-bold text-slate-900 leading-tight">
            {bin.scenes.length} scene{bin.scenes.length === 1 ? "" : "s"} not yet
            assigned
          </span>
        </div>
        <div className="ml-auto px-2 py-0.5 rounded bg-amber-100 border border-amber-200">
          <span className="text-xs font-bold text-amber-700">
            {pagesDisplay(bin.total_pages)} pgs
          </span>
        </div>
      </div>
      <div className="px-4 py-3 flex flex-col gap-1.5">
        {bin.scenes.map((s, i) => (
          <SceneStrip
            key={s.id ?? i}
            scene={s}
            days={days}
            currentDayId={null}
            busy={busy}
            onMove={onMove}
          />
        ))}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// DayBlock
// -----------------------------------------------------------------------------

interface DayBlockProps {
  day: StripboardDay;
  days: StripboardDay[];
  expanded: boolean;
  busy: boolean;
  onToggle: () => void;
  onMove: (sceneId: string, target: string) => void;
  onDelete: () => void;
}

function DayBlock({
  day,
  days,
  expanded,
  busy,
  onToggle,
  onMove,
  onDelete,
}: DayBlockProps) {
  const castCount = useMemo(() => {
    const names = new Set<string>();
    for (const s of day.scenes) {
      for (const c of s.cast_ids) names.add(c);
    }
    return names.size;
  }, [day.scenes]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="w-full flex items-center gap-3 px-4 py-3 hover:bg-blue-50/30 transition-colors">
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-3 text-left flex-1 min-w-0"
        >
          {expanded ? (
            <ChevronDown size={14} className="text-blue-500 shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-slate-400 shrink-0" />
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
        </button>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <Clock size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">Call TBD</span>
          </div>
          <div className="flex items-center gap-1">
            <Film size={11} className="text-slate-400" />
            <span className="text-[11px] text-slate-500">{day.scenes.length} scenes</span>
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
          <button
            type="button"
            onClick={onDelete}
            disabled={busy}
            title={`Delete Day ${day.day_number} (scenes return to Unscheduled)`}
            className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-100 bg-slate-50/40">
          {day.scenes.length === 0 ? (
            <p className="text-sm text-slate-500 italic py-3">
              No scenes assigned to this day yet — assign them from the
              Unscheduled bin using the “Assign ▾” menu.
            </p>
          ) : (
            <div className="flex flex-col gap-1.5 mt-2">
              {day.scenes.map((s, i) => (
                <SceneStrip
                  key={s.id ?? i}
                  scene={s}
                  days={days}
                  currentDayId={day.id}
                  busy={busy}
                  onMove={onMove}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// SceneStrip — with an inline placement <select> (Unscheduled / Day N).
// -----------------------------------------------------------------------------

interface SceneStripProps {
  scene: StripboardSceneSnapshot;
  days: StripboardDay[];
  currentDayId: string | null;
  busy: boolean;
  onMove: (sceneId: string, target: string) => void;
}

function SceneStrip({ scene, days, currentDayId, busy, onMove }: SceneStripProps) {
  const value = currentDayId ?? UNSCHEDULED;
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

      {/* Placement control */}
      <div className="flex items-center px-2 border-l border-slate-100">
        <select
          aria-label={`Assign scene ${scene.scene_number} to a day`}
          value={value}
          disabled={busy || !scene.id}
          onChange={(e) => {
            if (scene.id && e.target.value !== value) {
              onMove(scene.id, e.target.value);
            }
          }}
          className="text-[11px] border border-slate-200 rounded-md px-1.5 py-1 bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed max-w-[110px]"
        >
          <option value={UNSCHEDULED}>Unscheduled</option>
          {days.map((d) => (
            <option key={d.id} value={d.id}>
              Day {d.day_number}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
