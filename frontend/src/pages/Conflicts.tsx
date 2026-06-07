import { useState, useEffect } from 'react';
import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  Loader2, RefreshCw, GitMerge, Shield, Gavel,
} from 'lucide-react';
import type { DetectedConflict } from '../types';
import { conflictsApi } from '../api';

// -- Constants ----------------------------------------------------------------

const CONFLICT_TYPE_STYLES: Record<string, string> = {
  value_mismatch:      'bg-amber-100 text-amber-700',
  mutual_exclusivity:  'bg-red-100 text-red-700',
  contradiction:       'bg-orange-100 text-orange-700',
};

const STRATEGIES = [
  { name: 'strictest',             label: 'Strictest',             desc: 'Lowest credit / highest fee wins — conservative approach' },
  { name: 'most_generous',         label: 'Most Generous',         desc: 'Highest credit / lowest fee wins — maximize incentive value' },
  { name: 'jurisdiction_priority', label: 'Jurisdiction Priority', desc: 'Higher-level jurisdiction wins (state > county > city)' },
  { name: 'user_decides',          label: 'Flag for Review',       desc: 'Mark for manual review — use Override instead to choose a rule' },
];

function fmt(v: number | null): string {
  if (v === null) return '—';
  return v % 1 === 0 ? `${v}%` : `$${v.toLocaleString()}`;
}

// -- Resolution Modal ---------------------------------------------------------

interface ResolveModalProps {
  conflict: DetectedConflict;
  onClose: () => void;
  onDone: () => void;
}

function ResolveModal({ conflict, onClose, onDone }: ResolveModalProps) {
  const [strategy, setStrategy] = useState('most_generous');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleSubmit() {
    setSaving(true);
    setErr(null);
    try {
      await conflictsApi.resolve(conflict.id, { strategy_name: strategy, notes: notes || undefined });
      onDone();
    } catch {
      setErr('Failed to apply resolution. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Apply Resolution Strategy</h2>
          <p className="text-sm text-gray-500 mt-1">
            <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{conflict.ruleKey1}</span>
            {' vs '}
            <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{conflict.ruleKey2}</span>
          </p>
        </div>

        <div className="px-6 py-4 space-y-3">
          {STRATEGIES.map(s => (
            <label key={s.name} className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${strategy === s.name ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
              <input
                type="radio"
                name="strategy"
                value={s.name}
                checked={strategy === s.name}
                onChange={() => setStrategy(s.name)}
                className="mt-0.5 accent-blue-600"
              />
              <div>
                <div className="font-medium text-sm text-gray-900">{s.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{s.desc}</div>
              </div>
            </label>
          ))}

          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none mt-1"
          />

          {err && <p className="text-sm text-red-600">{err}</p>}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

// -- Override Modal -----------------------------------------------------------

interface OverrideModalProps {
  conflict: DetectedConflict;
  onClose: () => void;
  onDone: () => void;
}

function OverrideModal({ conflict, onClose, onDone }: OverrideModalProps) {
  const [chosenKey, setChosenKey] = useState(conflict.ruleKey1);
  const [chosenValue, setChosenValue] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleSubmit() {
    setSaving(true);
    setErr(null);
    try {
      await conflictsApi.override(conflict.id, {
        chosen_rule_key: chosenKey,
        chosen_value: chosenValue ? parseFloat(chosenValue) : null,
        notes: notes || undefined,
      });
      onDone();
    } catch {
      setErr('Failed to save override. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Manual Override</h2>
          <p className="text-sm text-gray-500 mt-1">Choose which rule should prevail</p>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Choose rule</label>
            <div className="space-y-2">
              {[conflict.ruleKey1, conflict.ruleKey2].map(key => (
                <label key={key} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${chosenKey === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <input
                    type="radio"
                    name="chosenKey"
                    value={key}
                    checked={chosenKey === key}
                    onChange={() => setChosenKey(key)}
                    className="accent-blue-600"
                  />
                  <span className="font-mono text-sm text-gray-800">{key}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Override value (optional)</label>
            <input
              type="number"
              value={chosenValue}
              onChange={e => setChosenValue(e.target.value)}
              placeholder="e.g. 25 for 25%"
              className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />

          {err && <p className="text-sm text-red-600">{err}</p>}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Save Override
          </button>
        </div>
      </div>
    </div>
  );
}

// -- Conflict Row -------------------------------------------------------------

interface ConflictRowProps {
  conflict: DetectedConflict;
  onRefresh: () => void;
}

function ConflictRow({ conflict, onRefresh }: ConflictRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [modal, setModal] = useState<null | 'resolve' | 'override'>(null);

  const resolved = conflict.resolvedAt !== null;

  return (
    <>
      <div className={`border rounded-xl bg-white overflow-hidden ${resolved ? 'border-gray-200 opacity-75' : 'border-amber-200'}`}>
        {/* Row header */}
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            type="button"
            onClick={() => setExpanded(e => !e)}
            className="text-gray-400 hover:text-gray-600 shrink-0"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CONFLICT_TYPE_STYLES[conflict.conflictType] ?? 'bg-gray-100 text-gray-600'}`}>
                {conflict.conflictType.replace(/_/g, ' ')}
              </span>
              <span className="font-mono text-xs text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded">{conflict.ruleKey1}</span>
              <span className="text-gray-400 text-xs">vs</span>
              <span className="font-mono text-xs text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded">{conflict.ruleKey2}</span>
              {conflict.ruleType && (
                <span className="text-xs text-gray-500">{conflict.ruleType}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500 flex-wrap">
              <span className="font-medium text-gray-700">{conflict.jurisdiction?.name ?? conflict.jurisdictionId}</span>
              {conflict.value1 !== null && conflict.value2 !== null && (
                <span>{fmt(conflict.value1)} vs {fmt(conflict.value2)}</span>
              )}
              <span>{new Date(conflict.createdAt).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Status + actions */}
          <div className="flex items-center gap-2 shrink-0">
            {resolved ? (
              <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
              </span>
            ) : (
              <>
                <button
                  onClick={() => setModal('resolve')}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Shield className="w-3.5 h-3.5" /> Strategy
                </button>
                <button
                  onClick={() => setModal('override')}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Gavel className="w-3.5 h-3.5" /> Override
                </button>
              </>
            )}
          </div>
        </div>

        {/* Expanded detail */}
        {expanded && (
          <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-gray-500">Rule 1</span>
                <p className="font-mono text-gray-800 mt-0.5">{conflict.ruleKey1}</p>
                {conflict.jurisdictionName1 && <p className="text-gray-500">{conflict.jurisdictionName1}</p>}
                {conflict.value1 !== null && <p className="font-medium">{fmt(conflict.value1)}</p>}
              </div>
              <div>
                <span className="text-gray-500">Rule 2</span>
                <p className="font-mono text-gray-800 mt-0.5">{conflict.ruleKey2}</p>
                {conflict.jurisdictionName2 && <p className="text-gray-500">{conflict.jurisdictionName2}</p>}
                {conflict.value2 !== null && <p className="font-medium">{fmt(conflict.value2)}</p>}
              </div>
            </div>

            {resolved && (
              <div className="mt-2 p-2 bg-green-50 rounded-lg border border-green-200 text-xs space-y-0.5">
                <p className="font-medium text-green-800">
                  Resolved via <span className="italic">{conflict.resolutionStrategy?.strategyName ?? 'user_decides'}</span>
                  {conflict.resolvedValue !== null && <> → {fmt(conflict.resolvedValue)}</>}
                </p>
                <p className="text-green-700">By {conflict.resolvedBy} on {new Date(conflict.resolvedAt!).toLocaleString()}</p>
                {conflict.notes && <p className="text-gray-600 italic">{conflict.notes}</p>}
              </div>
            )}

            {(conflict.userOverrides?.length ?? 0) > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-xs font-medium text-gray-600">User Overrides</p>
                {conflict.userOverrides!.map(o => (
                  <div key={o.id} className="text-xs p-2 bg-white rounded-lg border border-gray-200">
                    Chose <span className="font-mono">{o.chosenRuleKey}</span>
                    {o.chosenValue !== null && <> ({fmt(o.chosenValue)})</>}
                    {o.notes && <> — {o.notes}</>}
                    <span className="text-gray-400 ml-2">{new Date(o.chosenAt).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {modal === 'resolve' && (
        <ResolveModal conflict={conflict} onClose={() => setModal(null)} onDone={() => { setModal(null); onRefresh(); }} />
      )}
      {modal === 'override' && (
        <OverrideModal conflict={conflict} onClose={() => setModal(null)} onDone={() => { setModal(null); onRefresh(); }} />
      )}
    </>
  );
}

// -- Stats bar ----------------------------------------------------------------

function StatsBar({ total, unresolved }: { total: number; unresolved: number }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {[
        { label: 'Total Conflicts', value: total,            color: 'text-gray-900' },
        { label: 'Unresolved',      value: unresolved,       color: 'text-amber-600' },
        { label: 'Resolved',        value: total - unresolved, color: 'text-green-600' },
      ].map(({ label, value, color }) => (
        <div key={label} className="bg-white border border-gray-200 rounded-xl p-4 text-center">
          <div className={`text-2xl font-bold ${color}`}>{value}</div>
          <div className="text-xs text-gray-500 mt-0.5">{label}</div>
        </div>
      ))}
    </div>
  );
}

// -- Main page ----------------------------------------------------------------

export default function Conflicts() {
  const [conflicts, setConflicts] = useState<DetectedConflict[]>([]);
  const [total, setTotal] = useState(0);
  const [unresolvedTotal, setUnresolvedTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState('');
  const [unresolvedOnly, setUnresolvedOnly] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [all, unresolved] = await Promise.all([
        conflictsApi.list({ conflict_type: typeFilter || undefined, unresolved_only: unresolvedOnly }),
        conflictsApi.list({ unresolved_only: true }),
      ]);
      setConflicts(all.conflicts);
      setTotal(all.total);
      setUnresolvedTotal(unresolved.total);
    } catch {
      setError('Failed to load conflicts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [typeFilter, unresolvedOnly]);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
            <GitMerge className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Conflict Resolution</h1>
            <p className="text-sm text-gray-500">Review and resolve detected incentive rule conflicts</p>
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <StatsBar total={total} unresolved={unresolvedTotal} />

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Types</option>
          <option value="value_mismatch">Value Mismatch</option>
          <option value="mutual_exclusivity">Mutual Exclusivity</option>
          <option value="contradiction">Contradiction</option>
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={unresolvedOnly}
            onChange={e => setUnresolvedOnly(e.target.checked)}
            className="accent-blue-600 w-4 h-4"
          />
          Unresolved only
        </label>

        {(typeFilter || unresolvedOnly) && (
          <button
            onClick={() => { setTypeFilter(''); setUnresolvedOnly(false); }}
            className="text-xs text-gray-500 hover:text-gray-800 underline"
          >
            Clear filters
          </button>
        )}

        <span className="ml-auto text-sm text-gray-400">{conflicts.length} shown</span>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      ) : conflicts.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-green-400" />
          <p className="font-medium text-gray-600">No conflicts found</p>
          <p className="text-sm mt-1">Run the stacking engine on a jurisdiction to detect conflicts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {conflicts.map(c => (
            <ConflictRow key={c.id} conflict={c} onRefresh={load} />
          ))}
        </div>
      )}
    </div>
  );
}
