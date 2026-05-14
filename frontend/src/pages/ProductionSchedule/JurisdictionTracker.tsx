// =============================================================================
// frontend/src/pages/ProductionSchedule/JurisdictionTracker.tsx
// 4-column table of per-jurisdiction shoot-day counts + a "Push to
// Compliance Bridge" button that calls
// POST /production-schedule/{productionId}/compliance-bridge/push.
//
// Phase 10 doesn't expose a /verify endpoint, so the button surfaces
// the brief's compliance-push action only; a per-row Verify control
// would land alongside a future POST /jurisdiction-tracker/verify.
// =============================================================================

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle,
  ClipboardCheck,
  Globe,
  Loader2,
  RefreshCcw,
  Send,
} from "lucide-react";

import {
  getJurisdictionTracker,
  pushCompliance,
  type JurisdictionTrackerRow,
  type CompliancePushPayload,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

function formatVerifiedAt(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export default function JurisdictionTracker({ productionId }: Props) {
  const [rows, setRows] = useState<JurisdictionTrackerRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState<CompliancePushPayload | null>(
    null,
  );

  function load() {
    if (!productionId) return;
    setError(null);
    return getJurisdictionTracker(productionId)
      .then((r) => {
        setRows(r);
      })
      .catch((e: unknown) => {
        setError(
          e instanceof Error
            ? e.message
            : "Could not load jurisdiction tracker.",
        );
      });
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setPushResult(null);
    load()?.finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productionId]);

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  async function handlePush() {
    if (pushing) return;
    setPushing(true);
    setPushResult(null);
    setError(null);
    try {
      const payload = await pushCompliance(productionId);
      setPushResult(payload);
      // Refresh the table so verified_at timestamps stay current.
      await load();
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not push to the Compliance Bridge.",
      );
    } finally {
      setPushing(false);
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3 text-blue-500" />
        <p className="text-sm">Loading jurisdiction tracker…</p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-2 bg-white text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {refreshing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCcw className="w-4 h-4" />
          )}
          Refresh
        </button>
        <button
          type="button"
          onClick={handlePush}
          disabled={pushing || rows.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {pushing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          Push to Compliance Bridge
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {pushResult && (
        <div className="p-4 rounded-lg border bg-emerald-50 border-emerald-200 text-emerald-900 text-sm flex items-start gap-2">
          <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            Pushed {Object.keys(pushResult).length}{" "}
            verified{" "}
            {Object.keys(pushResult).length === 1 ? "record" : "records"} to the
            Compliance Bridge. The Incentive Calculator now has the latest
            per-jurisdiction shoot-day counts for this production.
          </span>
        </div>
      )}

      {rows.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <Globe className="w-10 h-10 mx-auto text-slate-300 mb-3" />
          <h2 className="text-lg font-semibold text-slate-900">
            No jurisdiction records yet
          </h2>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            Once shoot days are pinned to jurisdictions in the stripboard,
            their counts will appear here for verification.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Jurisdiction
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Shoot Days
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Verified At
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => {
                const verified = !!r.verified_at;
                return (
                  <tr
                    key={r.jurisdiction_id}
                    className="hover:bg-slate-50/60 transition-colors"
                  >
                    <td className="px-6 py-3.5">
                      <div className="font-medium text-slate-900">
                        {r.jurisdiction_name}
                      </div>
                      {r.jurisdiction_name !== r.jurisdiction_id && (
                        <div className="text-[11px] text-slate-400">
                          {r.jurisdiction_id}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      <span className="font-mono text-base font-bold text-blue-600">
                        {r.shoot_days}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {formatVerifiedAt(r.verified_at)}
                    </td>
                    <td className="px-6 py-3.5">
                      {verified ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <ClipboardCheck className="w-3 h-3" />
                          Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                          <AlertCircle className="w-3 h-3" />
                          Unverified
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
