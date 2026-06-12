// =============================================================================
// frontend/src/pages/SignalDashboard.tsx
// Signal Dashboard — displays active production signals with severity indicators
// The visual face of the Autonomous Production OS
// =============================================================================
import { useEffect, useState } from "react";
import { AlertTriangle, AlertCircle, Info, CheckCircle2, RefreshCw, CheckCheck } from "lucide-react";

interface Signal {
  id: string;
  productionId: string;
  signalType: string;
  severity: string;
  source: string | null;
  entityType: string | null;
  message: string;
  resolved: boolean;
  resolvedAt: string | null;
  createdAt: string;
}

interface Props {
  productionId: string;
  token: string;
}

const SEVERITY_CONFIG: Record<string, { label: string; bg: string; border: string; text: string; icon: React.ReactNode }> = {
  critical: {
    label: "Critical",
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    icon: <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />,
  },
  high: {
    label: "High",
    bg: "bg-orange-50",
    border: "border-orange-200",
    text: "text-orange-800",
    icon: <AlertTriangle className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />,
  },
  medium: {
    label: "Medium",
    bg: "bg-yellow-50",
    border: "border-yellow-200",
    text: "text-yellow-800",
    icon: <AlertTriangle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />,
  },
  low: {
    label: "Low",
    bg: "bg-blue-50",
    border: "border-blue-100",
    text: "text-blue-800",
    icon: <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />,
  },
};

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  budget_drift:    "Budget Drift",
  ot_spike:        "OT Spike",
  weather_risk:    "Weather Risk",
  schedule_slip:   "Schedule Slip",
  vfx_inflation:   "VFX Inflation",
  crew_conflict:   "Crew Conflict",
  location_issue:  "Location Issue",
};

const SOURCE_LABELS: Record<string, string> = {
  aura:       "AURA",
  compliance: "Compliance Engine",
  budget:     "Budget Engine",
  manual:     "Manual",
};

export default function SignalDashboard({ productionId, token }: Props) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);

  const loadSignals = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/0.1.0/productions/${productionId}/signals/active`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error(`Failed to load signals: ${res.status}`);
      const data = await res.json();
      setSignals(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (productionId) loadSignals();
  }, [productionId]);

  const resolveSignal = async (signalId: string) => {
    setResolving(signalId);
    try {
      const res = await fetch(
        `/api/0.1.0/productions/${productionId}/signals/${signalId}/resolve`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ resolvedBy: "user" }),
        }
      );
      if (!res.ok) throw new Error("Failed to resolve signal");
      await loadSignals();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not resolve signal");
    } finally {
      setResolving(null);
    }
  };

  const criticalCount = signals.filter(s => s.severity === "critical").length;
  const highCount = signals.filter(s => s.severity === "high").length;
  const mediumCount = signals.filter(s => s.severity === "medium").length;
  const lowCount = signals.filter(s => s.severity === "low").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Production Intelligence</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Active signals — the platform is watching your production
          </p>
        </div>
        <button
          onClick={loadSignals}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Severity Summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Critical", count: criticalCount, bg: "bg-red-50", border: "border-red-200", text: "text-red-700", dot: "bg-red-500" },
          { label: "High", count: highCount, bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", dot: "bg-orange-500" },
          { label: "Medium", count: mediumCount, bg: "bg-yellow-50", border: "border-yellow-200", text: "text-yellow-700", dot: "bg-yellow-500" },
          { label: "Low", count: lowCount, bg: "bg-blue-50", border: "border-blue-100", text: "text-blue-700", dot: "bg-blue-500" },
        ].map(s => (
          <div key={s.label} className={`${s.bg} ${s.border} border rounded-xl p-4`}>
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${s.dot}`} />
              <span className={`text-xs font-semibold uppercase tracking-wider ${s.text}`}>{s.label}</span>
            </div>
            <div className={`text-2xl font-bold ${s.text}`}>{s.count}</div>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
          {error}
        </div>
      )}

      {/* Signal List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      ) : signals.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <CheckCircle2 className="w-10 h-10 mx-auto text-green-400 mb-3" />
          <h3 className="text-lg font-semibold text-slate-900">All clear</h3>
          <p className="text-sm text-slate-500 mt-1">
            No active signals. The platform is monitoring your production.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {signals.map(signal => {
            const config = SEVERITY_CONFIG[signal.severity] || SEVERITY_CONFIG.low;
            return (
              <div
                key={signal.id}
                className={`${config.bg} ${config.border} border rounded-xl p-4`}
              >
                <div className="flex items-start gap-3">
                  {config.icon}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${config.text}`}>
                        {config.label}
                      </span>
                      <span className="text-xs bg-white border border-slate-200 text-slate-600 px-2 py-0.5 rounded-full">
                        {SIGNAL_TYPE_LABELS[signal.signalType] || signal.signalType}
                      </span>
                      {signal.source && (
                        <span className="text-xs text-slate-400">
                          via {SOURCE_LABELS[signal.source] || signal.source}
                        </span>
                      )}
                    </div>
                    <p className={`text-sm font-medium ${config.text}`}>{signal.message}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {new Date(signal.createdAt).toLocaleDateString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                      })}
                    </p>
                  </div>
                  <button
                    onClick={() => resolveSignal(signal.id)}
                    disabled={resolving === signal.id}
                    title="Mark resolved"
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 hover:text-green-600 hover:border-green-200 disabled:opacity-50 shrink-0"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    {resolving === signal.id ? "Resolving..." : "Resolve"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer note */}
      {signals.length > 0 && (
        <p className="text-xs text-slate-400 text-center">
          {signals.length} active signal{signals.length !== 1 ? "s" : ""} — resolve each as you address the underlying issue
        </p>
      )}
    </div>
  );
}
