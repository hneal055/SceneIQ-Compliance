import { useState } from "react";
import {
  Calendar,
  Clock,
  MapPin,
  Users,
  Film,
  Plus,
  ChevronDown,
  ChevronRight,
  Sun,
  Moon,
  Sunrise,
  LayoutGrid,
  List,
  Download,
  Filter,
  AlertCircle,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

type IntExt = "INT" | "EXT" | "INT/EXT";
type DayNight = "DAY" | "NIGHT" | "DAWN" | "DUSK";
type StripColor =
  | "action"
  | "dialogue"
  | "vfx"
  | "stunt"
  | "travel"
  | "insert"
  | "end";

interface CastMember {
  id: number;
  name: string;
  role: string;
}

interface Scene {
  id: string;
  sceneNumber: string;
  intExt: IntExt;
  dayNight: DayNight;
  location: string;
  setName: string;
  synopsis: string;
  pages: number; // stored as eighths e.g. 8 = 1 page, 4 = 4/8
  cast: CastMember[];
  stripType: StripColor;
  notes?: string;
}

interface ShootingDay {
  id: string;
  dayNumber: number;
  date: string;
  scenes: Scene[];
  callTime: string;
  wrapTime?: string;
  location?: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const CAST: CastMember[] = [
  { id: 1, name: "Dr. Nina Ortiz", role: "LEAD" },
  { id: 2, name: "Commander Reyes", role: "SUPPORTING" },
  { id: 3, name: "The Archivist", role: "SUPPORTING" },
  { id: 4, name: "Marcus Webb", role: "DAY PLAYER" },
  { id: 5, name: "Ancient Soldier", role: "DAY PLAYER" },
];

const MOCK_DAYS: ShootingDay[] = [
  {
    id: "day-1",
    dayNumber: 1,
    date: "2026-06-02",
    callTime: "06:00 AM",
    wrapTime: "07:30 PM",
    location: "Chicago — Stage 4",
    scenes: [
      {
        id: "s1",
        sceneNumber: "1",
        intExt: "INT",
        dayNight: "DAY",
        location: "FORENSIC LAB",
        setName: "Chicago Field Museum — Lower Level",
        synopsis: "Nina examines ancient remains. The quantum signature activates.",
        pages: 6,
        cast: [CAST[0], CAST[2]],
        stripType: "dialogue",
      },
      {
        id: "s2",
        sceneNumber: "4",
        intExt: "INT",
        dayNight: "NIGHT",
        location: "TRANSIT CORRIDOR",
        setName: "Chicago Field Museum — Hallway",
        synopsis: "Nina follows the signal. Discovers the gateway.",
        pages: 4,
        cast: [CAST[0]],
        stripType: "action",
      },
      {
        id: "s3",
        sceneNumber: "5A",
        intExt: "EXT",
        dayNight: "DAWN",
        location: "THE HOT GATES",
        setName: "VFX Plate — Thermopylae",
        synopsis: "Nina materializes in 480 BC. The battle rages around her.",
        pages: 8,
        cast: [CAST[0], CAST[4]],
        stripType: "vfx",
      },
    ],
  },
  {
    id: "day-2",
    dayNumber: 2,
    date: "2026-06-03",
    callTime: "07:00 AM",
    wrapTime: "08:00 PM",
    location: "Location — Grant Park",
    scenes: [
      {
        id: "s4",
        sceneNumber: "7",
        intExt: "EXT",
        dayNight: "DAY",
        location: "OPEN BATTLEFIELD",
        setName: "Grant Park — North End",
        synopsis: "Nina moves through the Persian advance. Encounters Reyes.",
        pages: 12,
        cast: [CAST[0], CAST[1], CAST[4]],
        stripType: "stunt",
        notes: "Stunt coordinator required. 40 BG.",
      },
      {
        id: "s5",
        sceneNumber: "8",
        intExt: "INT/EXT",
        dayNight: "DAY",
        location: "SPARTAN CAMP",
        setName: "Grant Park — Tent City",
        synopsis:
          "Reyes explains the mission. Nina realizes she can't change history.",
        pages: 10,
        cast: [CAST[0], CAST[1]],
        stripType: "dialogue",
      },
    ],
  },
  {
    id: "day-3",
    dayNumber: 3,
    date: "2026-06-04",
    callTime: "05:30 AM",
    location: "Chicago — Stage 4 / VFX Unit",
    scenes: [
      {
        id: "s6",
        sceneNumber: "12",
        intExt: "INT",
        dayNight: "NIGHT",
        location: "QUANTUM CHAMBER",
        setName: "Stage 4 — Chamber Set",
        synopsis: "The Archivist reveals the truth about the leaps.",
        pages: 16,
        cast: [CAST[0], CAST[2]],
        stripType: "dialogue",
      },
      {
        id: "s7",
        sceneNumber: "INSERT-A",
        intExt: "INT",
        dayNight: "DAY",
        location: "VARIOUS INSERTS",
        setName: "Stage 4 — Insert Stage",
        synopsis: "Close-up inserts: hands, devices, artifacts.",
        pages: 2,
        cast: [],
        stripType: "insert",
      },
    ],
  },
];

// ─── Strip Color Config ───────────────────────────────────────────────────────

const STRIP_CONFIG: Record<
  StripColor,
  { bg: string; border: string; label: string; dot: string }
> = {
  action:   { bg: "bg-yellow-500/15", border: "border-l-yellow-400",  label: "Action",   dot: "bg-yellow-400" },
  dialogue: { bg: "bg-blue-500/15",   border: "border-l-blue-400",    label: "Dialogue", dot: "bg-blue-400" },
  vfx:      { bg: "bg-purple-500/15", border: "border-l-purple-400",  label: "VFX",      dot: "bg-purple-400" },
  stunt:    { bg: "bg-red-500/15",    border: "border-l-red-400",     label: "Stunt",    dot: "bg-red-400" },
  travel:   { bg: "bg-green-500/15",  border: "border-l-green-400",   label: "Travel",   dot: "bg-green-400" },
  insert:   { bg: "bg-gray-500/15",   border: "border-l-gray-400",    label: "Insert",   dot: "bg-gray-400" },
  end:      { bg: "bg-slate-500/15",  border: "border-l-slate-400",   label: "End Day",  dot: "bg-slate-400" },
};

// ─── Helper Functions ─────────────────────────────────────────────────────────

const pagesDisplay = (eighths: number) => {
  const full = Math.floor(eighths / 8);
  const rem = eighths % 8;
  if (rem === 0) return `${full}`;
  if (full === 0) return `${rem}/8`;
  return `${full} ${rem}/8`;
};

const totalPages = (scenes: Scene[]) =>
  scenes.reduce((sum, s) => sum + s.pages, 0);

const dayNightIcon = (dn: DayNight) => {
  if (dn === "DAY")  return <Sun size={11} className="text-yellow-300" />;
  if (dn === "NIGHT") return <Moon size={11} className="text-blue-300" />;
  return <Sunrise size={11} className="text-orange-300" />;
};

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric",
  });

// ─── Sub-components ───────────────────────────────────────────────────────────

function SceneStrip({ scene }: { scene: Scene }) {
  const config = STRIP_CONFIG[scene.stripType];
  return (
    <div
      className={`
        flex items-stretch rounded-md border border-white/5
        border-l-4 ${config.border} ${config.bg}
        hover:border-white/20 transition-all duration-150 group cursor-pointer
      `}
    >
      {/* Scene number */}
      <div className="flex flex-col items-center justify-center px-3 py-2 min-w-[48px] border-r border-white/5">
        <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Sc</span>
        <span className="text-sm font-bold text-white/90 leading-tight">{scene.sceneNumber}</span>
      </div>

      {/* Main info */}
      <div className="flex-1 px-3 py-2 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[10px] font-mono font-bold text-white/50 tracking-wider">
            {scene.intExt}
          </span>
          <span className="flex items-center gap-0.5">
            {dayNightIcon(scene.dayNight)}
            <span className="text-[10px] text-white/40">{scene.dayNight}</span>
          </span>
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${config.bg} ${config.dot.replace("bg-", "text-")}`}>
            {config.label}
          </span>
        </div>
        <p className="text-xs font-semibold text-white/80 truncate">{scene.location}</p>
        <p className="text-[11px] text-white/40 truncate mt-0.5">{scene.synopsis}</p>
      </div>

      {/* Cast */}
      <div className="hidden md:flex flex-col justify-center px-3 py-2 min-w-[120px] border-l border-white/5">
        {scene.cast.length === 0 ? (
          <span className="text-[10px] text-white/25 italic">No cast</span>
        ) : (
          scene.cast.slice(0, 2).map((c) => (
            <span key={c.id} className="text-[10px] text-white/50 truncate">{c.name}</span>
          ))
        )}
        {scene.cast.length > 2 && (
          <span className="text-[10px] text-white/30">+{scene.cast.length - 2} more</span>
        )}
      </div>

      {/* Pages */}
      <div className="flex flex-col items-center justify-center px-3 py-2 min-w-[56px] border-l border-white/5">
        <span className="text-sm font-bold text-[#C9973A]">{pagesDisplay(scene.pages)}</span>
        <span className="text-[9px] text-white/30 uppercase tracking-wider">pgs</span>
      </div>

      {/* Notes indicator */}
      {scene.notes && (
        <div className="flex items-center px-2 border-l border-white/5">
          <AlertCircle size={12} className="text-orange-400" />
        </div>
      )}
    </div>
  );
}

function DayBlock({
  day,
  expanded,
  onToggle,
}: {
  day: ShootingDay;
  expanded: boolean;
  onToggle: () => void;
}) {
  const pages = totalPages(day.scenes);
  const uniqueCast = Array.from(
    new Map(
      day.scenes.flatMap((s) => s.cast).map((c) => [c.id, c])
    ).values()
  );

  return (
    <div className="mb-3">
      {/* Day header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-white/5 hover:bg-white/8 border border-white/10 hover:border-[#C9973A]/30 transition-all duration-200 group"
      >
        <div className="flex items-center gap-2">
          {expanded
            ? <ChevronDown size={14} className="text-[#C9973A]" />
            : <ChevronRight size={14} className="text-white/40 group-hover:text-[#C9973A]" />
          }
          <div className="flex flex-col items-start">
            <span className="text-[10px] font-mono text-[#C9973A] uppercase tracking-widest">
              Day {day.dayNumber}
            </span>
            <span className="text-sm font-bold text-white/90 leading-tight">
              {formatDate(day.date)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 ml-2">
          <MapPin size={11} className="text-white/30" />
          <span className="text-[11px] text-white/40 text-left">{day.location}</span>
        </div>

        <div className="ml-auto flex items-center gap-4">
          <div className="flex items-center gap-1">
            <Clock size={11} className="text-white/30" />
            <span className="text-[11px] text-white/50">{day.callTime}</span>
            {day.wrapTime && (
              <span className="text-[11px] text-white/30"> — {day.wrapTime}</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Film size={11} className="text-white/30" />
            <span className="text-[11px] text-white/50">{day.scenes.length} scenes</span>
          </div>
          <div className="flex items-center gap-1">
            <Users size={11} className="text-white/30" />
            <span className="text-[11px] text-white/50">{uniqueCast.length} cast</span>
          </div>
          <div className="px-2 py-0.5 rounded bg-[#C9973A]/15 border border-[#C9973A]/20">
            <span className="text-xs font-bold text-[#C9973A]">{pagesDisplay(pages)} pgs</span>
          </div>
        </div>
      </button>

      {/* Scene strips */}
      {expanded && (
        <div className="mt-1.5 ml-4 pl-4 border-l border-white/5 flex flex-col gap-1.5">
          {day.scenes.map((scene) => (
            <SceneStrip key={scene.id} scene={scene} />
          ))}
          <button className="flex items-center gap-2 px-3 py-2 rounded-md text-[11px] text-white/30 hover:text-white/60 hover:bg-white/5 transition-all border border-dashed border-white/10 hover:border-white/20 mt-0.5">
            <Plus size={11} />
            Add scene to Day {day.dayNumber}
          </button>
        </div>
      )}
    </div>
  );
}

function LegendDot({ type }: { type: StripColor }) {
  const c = STRIP_CONFIG[type];
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${c.dot}`} />
      <span className="text-[10px] text-white/40">{c.label}</span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SchedulePage() {
  const [days] = useState<ShootingDay[]>(MOCK_DAYS);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(
    new Set(["day-1"])
  );
  const [view, setView] = useState<"stripboard" | "list">("stripboard");

  const toggleDay = (id: string) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const expandAll = () => setExpandedDays(new Set(days.map((d) => d.id)));
  const collapseAll = () => setExpandedDays(new Set());

  const totalScenes = days.reduce((sum, d) => sum + d.scenes.length, 0);
  const totalPgs = days.reduce((sum, d) => sum + totalPages(d.scenes), 0);
  const totalCast = new Set(
    days.flatMap((d) => d.scenes.flatMap((s) => s.cast.map((c) => c.id)))
  ).size;

  return (
    <div
      className="min-h-screen text-white"
      style={{
        background: "linear-gradient(160deg, #0d0d1a 0%, #111827 60%, #0a0a14 100%)",
        fontFamily: "'DM Sans', 'Inter', sans-serif",
      }}
    >
      {/* Top bar */}
      <div className="border-b border-white/8 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Calendar size={14} className="text-[#C9973A]" />
              <span className="text-[10px] font-mono text-[#C9973A] uppercase tracking-widest">
                SceneIQ · Schedule Engine
              </span>
            </div>
            <h1 className="text-xl font-bold text-white">
              Production Strip Board
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] text-white/50 hover:text-white/80 hover:bg-white/5 border border-white/10 transition-all">
              <Filter size={11} />
              Filter
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] text-white/50 hover:text-white/80 hover:bg-white/5 border border-white/10 transition-all">
              <Download size={11} />
              Export
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-semibold text-[#0d0d1a] bg-[#C9973A] hover:bg-[#d4a84d] transition-all">
              <Plus size={11} />
              Add Scene
            </button>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="border-b border-white/5 px-6 py-3 bg-white/2">
        <div className="max-w-6xl mx-auto flex items-center gap-6">
          {[
            { label: "Shooting Days", value: days.length, icon: <Calendar size={12} /> },
            { label: "Total Scenes", value: totalScenes, icon: <Film size={12} /> },
            { label: "Total Pages", value: pagesDisplay(totalPgs), icon: <LayoutGrid size={12} /> },
            { label: "Cast Members", value: totalCast, icon: <Users size={12} /> },
          ].map((stat) => (
            <div key={stat.label} className="flex items-center gap-2">
              <span className="text-white/25">{stat.icon}</span>
              <span className="text-lg font-bold text-white/90">{stat.value}</span>
              <span className="text-[10px] text-white/35 uppercase tracking-wider">{stat.label}</span>
            </div>
          ))}

          <div className="ml-auto flex items-center gap-1 p-0.5 rounded-md bg-white/5 border border-white/8">
            <button
              onClick={() => setView("stripboard")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-all ${
                view === "stripboard"
                  ? "bg-white/10 text-white"
                  : "text-white/35 hover:text-white/60"
              }`}
            >
              <LayoutGrid size={11} />
              Strip Board
            </button>
            <button
              onClick={() => setView("list")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-all ${
                view === "list"
                  ? "bg-white/10 text-white"
                  : "text-white/35 hover:text-white/60"
              }`}
            >
              <List size={11} />
              List
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Legend + controls */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-4 flex-wrap">
            {(["action", "dialogue", "vfx", "stunt", "insert"] as StripColor[]).map(
              (t) => <LegendDot key={t} type={t} />
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={expandAll}
              className="text-[11px] text-white/35 hover:text-[#C9973A] transition-colors"
            >
              Expand all
            </button>
            <span className="text-white/20">·</span>
            <button
              onClick={collapseAll}
              className="text-[11px] text-white/35 hover:text-[#C9973A] transition-colors"
            >
              Collapse all
            </button>
          </div>
        </div>

        {/* Day blocks */}
        <div>
          {days.map((day) => (
            <DayBlock
              key={day.id}
              day={day}
              expanded={expandedDays.has(day.id)}
              onToggle={() => toggleDay(day.id)}
            />
          ))}
        </div>

        {/* Add day */}
        <button className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-dashed border-white/10 hover:border-[#C9973A]/30 text-[11px] text-white/25 hover:text-[#C9973A] transition-all">
          <Plus size={12} />
          Add Shooting Day
        </button>
      </div>
    </div>
  );
}
