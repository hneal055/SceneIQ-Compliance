import { useState, useEffect } from 'react';
import { ExternalLink, Loader2, ChevronDown, ChevronUp, DollarSign, Percent, AlertCircle, ArrowLeft } from 'lucide-react';
import api from '../api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Program {
  id: string;
  name: string;
  code: string;
  incentive_type: string;
  credit_type?: string | null;
  percentage: number;
  min_spend: number | null;
  max_credit: number | null;
  eligible_expenses: string[] | null;
  excluded_expenses: string[] | null;
  requirements: string | string[] | null;
  effective_date: string | null;
  active: boolean;
}

const CREDIT_TYPE_STYLE: Record<string, string> = {
  refundable:     'bg-emerald-100 text-emerald-700',
  transferable:   'bg-blue-100 text-blue-700',
  non_refundable: 'bg-amber-100 text-amber-700',
  rebate:         'bg-violet-100 text-violet-700',
  grant:          'bg-sky-100 text-sky-700',
};
const CREDIT_TYPE_LABEL: Record<string, string> = {
  refundable:     'Refundable',
  transferable:   'Transferable',
  non_refundable: 'Non-Refundable',
  rebate:         'Cash Rebate',
  grant:          'Grant',
};

interface Props {
  code: string;
  name: string;
  onBack?: () => void;
  onNavigate?: (code: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt$(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : s;
}

// ─── StatCard ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
      <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-1">{label}</p>
      <p className="text-3xl font-black text-slate-900 leading-none">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1.5">{sub}</p>}
    </div>
  );
}

// ─── ProgramCard ──────────────────────────────────────────────────────────────

function ProgramCard({ program }: { program: Program }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
      <div
        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center shrink-0">
          <span className="text-emerald-700 font-black text-lg">{program.percentage}%</span>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-slate-900 truncate">{program.name}</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {program.code} &middot; {capitalize(program.incentive_type)}
            {program.min_spend != null && ` · Min spend ${fmt$(program.min_spend)}`}
            {program.max_credit != null && ` · Cap ${fmt$(program.max_credit)}`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {program.credit_type && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${CREDIT_TYPE_STYLE[program.credit_type] ?? 'bg-slate-100 text-slate-500'}`}>
              {CREDIT_TYPE_LABEL[program.credit_type] ?? program.credit_type}
            </span>
          )}
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${
            program.active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
          }`}>
            {program.active ? 'Active' : 'Inactive'}
          </span>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-slate-400" />
            : <ChevronDown className="w-4 h-4 text-slate-400" />
          }
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100 px-5 py-4 space-y-4 bg-slate-50/50">
          {program.eligible_expenses && program.eligible_expenses.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-2">Eligible Expenses</p>
              <div className="flex flex-wrap gap-1.5">
                {program.eligible_expenses.map(e => (
                  <span key={e} className="px-2.5 py-1 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700 font-medium">
                    {capitalize(e)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {program.excluded_expenses && program.excluded_expenses.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-2">Excluded Expenses</p>
              <div className="flex flex-wrap gap-1.5">
                {program.excluded_expenses.map(e => (
                  <span key={e} className="px-2.5 py-1 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600 font-medium">
                    {capitalize(e)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {program.requirements && program.requirements.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-2">Requirements</p>
              <ul className="space-y-1">
                {(typeof program.requirements === 'string'
                  ? program.requirements.split('\n')
                  : Array.isArray(program.requirements) ? program.requirements : []
                ).filter(Boolean).map((req, i) => {
                  const reqText = typeof req === 'string'
                    ? req
                    : (req as { description?: string }).description ?? '';
                  if (!reqText) return null;
                  return (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                      {reqText}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {program.effective_date && (
            <p className="text-xs text-slate-400">
              Effective: {new Date(program.effective_date).toLocaleDateString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Estimator ────────────────────────────────────────────────────────────────

function Estimator({ programs }: { programs: Program[] }) {
  const [budget, setBudget] = useState('');

  const activePrograms = programs.filter(p => p.active);
  const budgetNum = parseFloat(budget.replace(/[^0-9.]/g, '')) || 0;

  const estimates = activePrograms
    .filter(p => p.min_spend == null || budgetNum >= p.min_spend)
    .map(p => ({
      code:   p.code,
      rate:   p.percentage,
      amount: Math.min(budgetNum * (p.percentage / 100), p.max_credit ?? Infinity),
    }));

  const totalEstimate = estimates.reduce((sum, e) => sum + e.amount, 0);

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
      <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-3">Quick Estimator</p>

      <div className="relative mb-4">
        <DollarSign className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
        <input
          type="text"
          title="Total budget"
          placeholder="Total budget"
          value={budget}
          onChange={e => setBudget(e.target.value)}
          className="w-full pl-8 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {budgetNum > 0 ? (
        <div className="space-y-2">
          {estimates.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-2">Budget below minimum spend for active programs.</p>
          ) : (
            <>
              {estimates.map(e => (
                <div key={e.code} className="flex items-center justify-between text-xs">
                  <span className="text-slate-600">{e.code} ({e.rate}%)</span>
                  <span className="font-bold text-emerald-700">{fmt$(e.amount)}</span>
                </div>
              ))}
              <div className="border-t border-slate-100 pt-2 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700">Est. Total Credit</span>
                <span className="text-base font-black text-emerald-700">{fmt$(totalEstimate)}</span>
              </div>
              <p className="text-[10px] text-slate-400 leading-relaxed">
                Estimate only. Actual credits depend on qualifying expenses and agency approval.
              </p>
            </>
          )}
        </div>
      ) : (
        <p className="text-xs text-slate-400 text-center py-2">Enter a budget to see estimated credits.</p>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function JurisdictionDetail({ code, name, onBack, onNavigate }: Props) {
  const [programs,       setPrograms]       = useState<Program[]>([]);
  const [website,        setWebsite]        = useState<string | null>(null);
  const [currency,       setCurrency]       = useState<string>('USD');
  const [treatyPartners, setTreatyPartners] = useState<string[]>([]);
  const [isLoading,      setIsLoading]      = useState(true);
  const [error,          setError]          = useState<string | null>(null);
  const [parentName,     setParentName]     = useState<string | null>(null);
  const [parentRate,     setParentRate]     = useState<number>(0);

  // Derive parent code for sub-jurisdictions (e.g. LA-BATONROUGE → LA)
  const parentCode = code.includes('-') ? code.split('-')[0] : null;

  useEffect(() => {
    setIsLoading(true);
    setPrograms([]);
    setWebsite(null);
    setError(null);
    setParentName(null);
    setParentRate(0);

    api.georgia.getPrograms(code)
      .then(res => {
        setPrograms(res.programs);
        setCurrency(res.currency ?? 'USD');
        setTreatyPartners(res.treaty_partners ?? []);
      })
      .catch(() => setError(`Failed to load incentive data for ${name}.`))
      .finally(() => setIsLoading(false));

    api.georgia.getJurisdiction(code)
      .then(j => setWebsite(j.website ?? null))
      .catch(() => {});

    if (parentCode) {
      api.georgia.getJurisdiction(parentCode)
        .then(j => setParentName(j.name ?? parentCode))
        .catch(() => {});
      api.georgia.getPrograms(parentCode)
        .then(res => {
          const best = res.programs.filter((p: Program) => p.active)
            .reduce((max: number, p: Program) => Math.max(max, p.percentage), 0);
          setParentRate(best);
        })
        .catch(() => {});
    }
  }, [code, name, parentCode]);

  const activePrograms = programs.filter(p => p.active);
  const bestRate       = activePrograms.reduce((max, p) => Math.max(max, p.percentage), 0);
  const minSpend       = activePrograms.reduce((min, p) => p.min_spend != null ? Math.min(min, p.min_spend) : min, Infinity);
  const totalPotential = activePrograms.reduce((sum, p) => sum + p.percentage, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="w-8 h-8 text-red-400" />
        <p className="text-slate-600 font-medium">{error}</p>
        {onBack && (
          <button type="button" onClick={onBack} className="text-blue-600 text-sm hover:underline">
            Back to Jurisdictions
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-6 h-full min-h-0">

      {/* ── Left panel ─────────────────────────────────────────── */}
      <div className="w-72 shrink-0 flex flex-col gap-4">

        {/* Back button */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors self-start"
          >
            <ArrowLeft className="w-4 h-4" />
            All Jurisdictions
          </button>
        )}

        {/* Badge */}
        <div className="bg-[#13151a] rounded-2xl p-5 text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center text-white font-black text-2xl mx-auto mb-3">
            {code}
          </div>
          <h2 className="text-white font-bold text-lg">{name}</h2>
          <p className="text-slate-400 text-xs mt-1">Film, Television &amp; Digital Entertainment</p>
          {website && (
            <a
              href={website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              Official Site
            </a>
          )}
        </div>

        {/* Stats */}
        {bestRate > 0 && (
          <StatCard
            label="Base Credit Rate"
            value={`${bestRate}%`}
            sub={`On qualified ${name} expenditures`}
          />
        )}
        {activePrograms.length > 0 && (
          <StatCard
            label="Stackable Programs"
            value={`${activePrograms.length}`}
            sub={totalPotential > 0 ? `Up to ${totalPotential}% combined potential` : undefined}
          />
        )}
        {minSpend < Infinity && (
          <StatCard
            label="Min Spend"
            value={fmt$(minSpend)}
            sub="Minimum qualifying expenditure"
          />
        )}

        {/* Currency */}
        {currency && currency !== 'USD' && (
          <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
            <p className="text-[11px] font-bold text-amber-700 tracking-widest uppercase mb-1">Currency</p>
            <p className="text-lg font-black text-amber-800">{currency}</p>
            <p className="text-[11px] text-amber-600 mt-1">Incentive paid in local currency — FX rate applies at claim date.</p>
          </div>
        )}

        {/* Treaty Partners */}
        {treatyPartners.length > 0 && (
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
            <p className="text-[11px] font-bold text-indigo-600 tracking-widest uppercase mb-2">Co-Production Treaties</p>
            <div className="flex flex-wrap gap-1.5">
              {treatyPartners.map(t => (
                <span key={t} className="px-2 py-0.5 bg-white border border-indigo-200 text-indigo-700 text-[11px] font-bold rounded">
                  {t}
                </span>
              ))}
            </div>
            <p className="text-[11px] text-indigo-500 mt-2">Productions may qualify for incentives in multiple treaty countries simultaneously.</p>
          </div>
        )}

        {/* Estimator */}
        {programs.length > 0 && <Estimator programs={programs} />}

        {/* Note */}
        <div className="flex items-start gap-2 px-1">
          <Percent className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Incentive estimates are for planning purposes only. Consult a qualified production accountant for final tax decisions.
          </p>
        </div>
      </div>

      {/* ── Main content ───────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 gap-4 overflow-y-auto">

        <div>
          <h1 className="text-[28px] font-bold text-slate-900 tracking-tight leading-tight">
            {name} Film Tax Incentives
          </h1>
          <p className="text-slate-500 mt-1 text-[15px]">
            {activePrograms.length > 0
              ? `${activePrograms.length} active incentive program${activePrograms.length !== 1 ? 's' : ''}`
              : 'No active programs found'
            }
            {bestRate > 0 && ` · Up to ${bestRate}% credit rate`}
          </p>
        </div>

        {programs.length === 0 ? (
          <div className="space-y-3">
            {parentCode && parentName ? (
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-5 flex gap-4">
                <div className="w-9 h-9 bg-blue-100 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                  <AlertCircle className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-blue-900 mb-1">
                    No city-specific incentive program
                  </p>
                  <p className="text-sm text-blue-700 leading-relaxed">
                    {name} does not operate its own film incentive program.{' '}
                    <strong>{parentName} state incentives{parentRate > 0 ? ` (up to ${parentRate}%)` : ''}</strong> apply
                    to productions shooting here — the city location does not affect eligibility.
                  </p>
                  {onNavigate ? (
                    <button
                      type="button"
                      onClick={() => onNavigate(parentCode)}
                      className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors"
                    >
                      View {parentName} incentive programs →
                    </button>
                  ) : (
                    <p className="mt-2 text-xs text-blue-500">
                      Go back and select <strong>{parentName}</strong> to view state credit rates and requirements.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 bg-white rounded-xl border border-slate-100">
                <p className="text-slate-500 text-sm">No incentive programs found for {name}.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3 pb-4">
            {programs.map(p => (
              <ProgramCard key={p.id} program={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
