import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Loader2,
  Calculator as CalcIcon,
  BookOpen,
  ReceiptText,
  LayoutList,
  PlayCircle,
  ClipboardCheck,
  RefreshCw,
  Plus,
  Trash2,
  Pencil,
} from 'lucide-react';
import api from '../api';
import SignalDashboard from './SignalDashboard';
import type {
  Production,
  Jurisdiction,
  IncentiveRule,
  Expense,
  CalculationResult,
  ComplianceItem,
  ComplianceStats,
} from '../types';

type Tab = 'overview' | 'expenses' | 'calculator' | 'rules' | 'compliance' | 'signals';

const STATUS_COLORS: Record<string, string> = {
  planning:        'bg-blue-100 text-blue-800',
  pre_production:  'bg-violet-100 text-violet-800',
  production:      'bg-green-100 text-green-800',
  post_production: 'bg-amber-100 text-amber-800',
  completed:       'bg-slate-100 text-slate-700',
};

const STATUS_LABELS: Record<string, string> = {
  planning:        'Planning',
  pre_production:  'Pre-Production',
  production:      'Production',
  post_production: 'Post-Production',
  completed:       'Completed',
};

const COMPLIANCE_STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  pending:  { label: 'Pending',  cls: 'bg-slate-100 text-slate-600' },
  complete: { label: 'Complete', cls: 'bg-emerald-100 text-emerald-700' },
  waived:   { label: 'Waived',   cls: 'bg-amber-100 text-amber-700' },
  na:       { label: 'N/A',      cls: 'bg-slate-50 text-slate-400' },
};

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}
function fmtPct(n: number) { return `${n.toFixed(1)}%`; }
function capitalize(s: string) { return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' '); }

function StatCard({ label, value, sub, accent = false }: {
  label: string; value: string; sub?: string; accent?: boolean;
}) {
  return (
    <div className={`rounded-xl border p-5 ${accent ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-slate-200'}`}>
      <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${accent ? 'text-blue-200' : 'text-slate-500'}`}>{label}</p>
      <p className={`text-2xl font-bold ${accent ? 'text-white' : 'text-slate-900'}`}>{value}</p>
      {sub && <p className={`text-xs mt-1 ${accent ? 'text-blue-200' : 'text-slate-500'}`}>{sub}</p>}
    </div>
  );
}

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview',    label: 'Overview',        icon: <LayoutList className="w-3.5 h-3.5" /> },
  { id: 'expenses',    label: 'Expenses',         icon: <ReceiptText className="w-3.5 h-3.5" /> },
  { id: 'compliance',    label: 'Compliance',      icon: <ClipboardCheck className="w-3.5 h-3.5" /> },
  { id: 'signals',      label: 'Intelligence',    icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  { id: 'calculator',  label: 'Calculator',       icon: <CalcIcon className="w-3.5 h-3.5" /> },
  { id: 'rules',       label: 'Incentive Rules',  icon: <BookOpen className="w-3.5 h-3.5" /> },
];

interface Props {
  productionId: string;
  onBack: () => void;
}

export default function ProductionDetail({ productionId, onBack }: Props) {
  const [tab, setTab] = useState<Tab>('overview');
  const [production, setProduction] = useState<Production | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [expensesLoading, setExpensesLoading] = useState(false);
  const [showAddExpense, setShowAddExpense] = useState(false);
  const [expenseForm, setExpenseForm] = useState({ category: 'labor', description: '', amount: '', expenseDate: new Date().toISOString().split('T')[0], isQualifying: true, vendorName: '' });
  const [expenseSaving, setExpenseSaving] = useState(false);
  const [expenseGenerating, setExpenseGenerating] = useState(false);
﻿  const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
  const [editExpenseForm, setEditExpenseForm] = useState({ description: '', amount: '', isQualifying: true, vendorName: '', category: 'labor' });

  async function handleEditExpenseSave(expenseId: string) {
    try {
      const token = localStorage.getItem('sceneiq_token');
      const res = await fetch(`/api/0.1.0/productions/${productionId}/expenses/${expenseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...editExpenseForm, amount: parseFloat(editExpenseForm.amount) }),
      });
      if (!res.ok) throw new Error('Failed to save');
      setEditingExpenseId(null);
      loadExpenses();
    } catch { /* silent */ }
  }

  const [generateError, setGenerateError] = useState<string | null>(null);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [rules, setRules] = useState<IncentiveRule[]>([]);
  const [calcResult, setCalcResult] = useState<CalculationResult | null>(null);
  const [calcJurId, setCalcJurId] = useState('');
  const [budgetEdit, setBudgetEdit] = useState<{ total: string; qualifying: string } | null>(null);
  const [budgetSaving, setBudgetSaving] = useState(false);
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [compliance, setCompliance] = useState<ComplianceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);
  const [compLoading, setCompLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.productions.get(productionId),
      api.jurisdictions.list(),
    ])
      .then(([prod, jurs]) => {
        setProduction(prod);
        const activeJurs = jurs.filter((j: Jurisdiction) => j.active);
        setJurisdictions(activeJurs);
        setCalcJurId(prod.jurisdictionId || (activeJurs[0]?.id ?? ''));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [productionId]);

  useEffect(() => {
    if (!production?.jurisdictionId) return;
    api.incentiveRules.getByJurisdiction(production.jurisdictionId)
      .then(rules => setRules(rules.filter(rule => rule.active)))
      .catch(() => {});
  }, [production?.jurisdictionId]);

  function loadCompliance() {
    setCompLoading(true);
    api.compliance.list(productionId)
      .then(data => setCompliance(data))
      .catch(() => {})
      .finally(() => setCompLoading(false));
  }

  useEffect(() => {
    if (tab === 'compliance' && !compliance) loadCompliance();
    if (tab === 'expenses') loadExpenses();
  }, [tab]); // intentionally omits loadCompliance/loadExpenses to avoid infinite loop

  function loadExpenses() {
    setExpensesLoading(true);
    api.expenses.list(productionId)
      .then(data => setExpenses(data))
      .catch(() => {})
      .finally(() => setExpensesLoading(false));
  }

  async function handleSaveBudget() {
    if (!budgetEdit || !production) return;
    setBudgetSaving(true);
    setBudgetError(null);
    try {
      const token = localStorage.getItem('sceneiq_token');
      const res = await fetch(`/api/0.1.0/productions/${production.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          budgetTotal: parseFloat(budgetEdit.total) || 0,
          budgetQualifying: budgetEdit.qualifying ? parseFloat(budgetEdit.qualifying) : null,
        }),
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      const updated = await res.json();
      setProduction(p => p ? {
        ...p,
        budgetTotal: updated.budgetTotal,
        budgetQualifying: updated.budgetQualifying,
      } : p);
      setBudgetEdit(null);
    } catch (e) {
      setBudgetError(e instanceof Error ? e.message : 'Failed to save budget');
    } finally {
      setBudgetSaving(false);
    }
  }

  async function handleAddExpense(e: React.FormEvent) {
    e.preventDefault();
    if (!expenseForm.description || !expenseForm.amount) return;
    setExpenseSaving(true);
    try {
      await api.expenses.create(productionId, {
        ...expenseForm,
        amount: parseFloat(expenseForm.amount),
      });
      setExpenseForm({ category: 'labor', description: '', amount: '', expenseDate: new Date().toISOString().split('T')[0], isQualifying: true, vendorName: '' });
      setShowAddExpense(false);
      loadExpenses();
    } catch { /* silent */ } finally { setExpenseSaving(false); }
  }

  async function handleDeleteExpense(expenseId: string) {
    try {
      await api.expenses.delete(productionId, expenseId);
      loadExpenses();
    } catch { /* silent */ }
  }

  async function handleGenerateExpenses(replace = false) {
    setExpenseGenerating(true);
    setGenerateError(null);
    try {
      await api.expenses.generate(productionId, replace);
      loadExpenses();
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setExpenseGenerating(false);
    }
  }

  async function handleCalculate() {
    if (!calcJurId) return;
    setCalcLoading(true); setCalcResult(null); setCalcError(null);
    try {
      const result = await api.calculations.calculate(productionId, calcJurId);
      setCalcResult(result);
    } catch (e) {
      setCalcError(e instanceof Error ? e.message : 'Calculation failed');
    } finally {
      setCalcLoading(false);
    }
  }

  async function handleGenerateChecklist() {
    setCompLoading(true);
    try {
      await api.compliance.generate(productionId);
      loadCompliance();
    } catch { setCompLoading(false); }
  }

  async function cycleStatus(item: ComplianceItem) {
    const cycle: ComplianceItem['status'][] = ['pending', 'complete', 'waived', 'na'];
    const next = cycle[(cycle.indexOf(item.status) + 1) % cycle.length];
    try {
      await api.compliance.updateItem(item.id, { status: next });
      loadCompliance();
    } catch { /* silent */ }
  }

  const totalSpend = expenses.reduce((s, i) => s + i.amount, 0);
  const qualifyingSpend = expenses.reduce((s, i) => s + (i.isQualifying ? i.amount : 0), 0);
  const jur = jurisdictions.find(j => j.id === production?.jurisdictionId);

  if (loading) {
    return <div className="flex justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }
  if (!production) {
    return <div className="p-8 text-center">Production not found. <button onClick={onBack} className="text-blue-600 underline">Go back</button></div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-8 py-6">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Productions
        </button>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-[26px] font-bold text-slate-900">{production.title}</h1>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_COLORS[production.status] ?? 'bg-slate-100'}`}>
                {STATUS_LABELS[production.status] ?? production.status}
              </span>
            </div>
            <p className="text-slate-500 text-sm">
              {production.productionCompany}{jur ? ` Â· ${jur.name}` : ''} Â· {capitalize(production.productionType)} Â· Started {production.startDate?.split('T')[0]}
            </p>
          </div>
          <div className="flex items-center gap-5">
            {/* Budget display / inline edit */}
            <div className="text-right">
              <p className="text-xs text-slate-400 font-medium">Total Budget</p>
              {budgetEdit ? (
                <div className="flex items-center gap-2 mt-1">
                  <div className="text-left">
                    <p className="text-[10px] text-slate-400 mb-0.5">Total ($)</p>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={budgetEdit.total}
                      onChange={e => setBudgetEdit(b => b ? { ...b, total: e.target.value } : b)}
                      className="w-32 px-2 py-1 border border-slate-300 rounded text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="text-left">
                    <p className="text-[10px] text-slate-400 mb-0.5">Qualifying ($)</p>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={budgetEdit.qualifying}
                      onChange={e => setBudgetEdit(b => b ? { ...b, qualifying: e.target.value } : b)}
                      className="w-32 px-2 py-1 border border-slate-300 rounded text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="optional"
                    />
                  </div>
                  <div className="flex flex-col gap-1 pt-4">
                    <button
                      onClick={handleSaveBudget}
                      disabled={budgetSaving}
                      className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50"
                    >
                      {budgetSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                      {budgetSaving ? 'Savingâ€¦' : 'Save'}
                    </button>
                    <button
                      onClick={() => { setBudgetEdit(null); setBudgetError(null); }}
                      className="px-3 py-1 bg-slate-100 text-slate-600 rounded text-xs hover:bg-slate-200"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <p className="text-xl font-bold text-slate-900">{fmt(production.budgetTotal)}</p>
                  <button
                    title="Edit budget"
                    onClick={() => setBudgetEdit({
                      total: String(production.budgetTotal),
                      qualifying: String(production.budgetQualifying ?? ''),
                    })}
                    className="text-slate-300 hover:text-blue-500 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
              {budgetError && <p className="text-xs text-red-600 mt-1">{budgetError}</p>}
            </div>
            {compliance && compliance.total > 0 && (
              <div className="text-right">
                <p className="text-xs text-slate-400 font-medium">Compliance</p>
                <p className="text-xl font-bold text-emerald-600">{compliance.pct}%</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-slate-200 px-8">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} className={`flex items-center gap-1.5 px-4 py-3.5 text-sm font-medium border-b-2 transition-colors ${tab === t.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              {t.icon}{t.label}
              {t.id === 'compliance' && compliance && compliance.total > 0 && (
                <span className={`ml-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${compliance.pct === 100 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{compliance.pct}%</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-8 max-w-6xl mx-auto">

        {/* Overview Tab */}
        {tab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Budget" value={fmt(production.budgetTotal)} />
              <StatCard label="Total Spend" value={expenses.length ? fmt(totalSpend) : 'â€”'} sub={`${expenses.length} items`} />
              <StatCard label="Qualifying Spend" value={expenses.length ? fmt(qualifyingSpend) : 'â€”'} sub={totalSpend ? fmtPct((qualifyingSpend / totalSpend) * 100) + ' of spend' : undefined} accent />
              <StatCard label="Incentive Rules" value={String(rules.length)} sub={jur?.name ?? 'No jurisdiction'} />
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-slate-900">Production Details</h2>
                {!budgetEdit && (
                  <button
                    onClick={() => setBudgetEdit({
                      total: String(production.budgetTotal),
                      qualifying: String(production.budgetQualifying ?? ''),
                    })}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
                  >
                    <Pencil className="w-3 h-3" /> Edit Budget
                  </button>
                )}
              </div>
              <dl className="grid grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-4 text-sm">
                {[
                  ['Title', production.title],
                  ['Type', capitalize(production.productionType)],
                  ['Company', production.productionCompany],
                  ['Status', STATUS_LABELS[production.status] ?? production.status],
                  ['Jurisdiction', jur ? `${jur.name} (${jur.code})` : 'â€”'],
                  ['Total Budget', fmt(production.budgetTotal)],
                  ['Qualifying Budget', production.budgetQualifying ? fmt(production.budgetQualifying) : 'â€”'],
                  ['Start Date', production.startDate?.split('T')[0] ?? 'â€”'],
                  ['End Date', production.endDate?.split('T')[0] ?? 'â€”'],
                  ['Created', production.createdAt?.split('T')[0] ?? 'â€”'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-slate-500 font-medium mb-0.5">{label}</dt>
                    <dd className="text-slate-900 font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        )}

        {/* Expenses Tab */}
        {tab === 'expenses' && (
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Total Spend" value={expenses.length ? fmt(totalSpend) : 'â€”'} sub={`${expenses.length} line items`} />
              <StatCard label="Qualifying" value={expenses.length ? fmt(qualifyingSpend) : 'â€”'} sub={totalSpend ? fmtPct((qualifyingSpend / totalSpend) * 100) + ' of spend' : undefined} accent />
              <StatCard label="Non-Qualifying" value={expenses.length ? fmt(totalSpend - qualifyingSpend) : 'â€”'} />
            </div>
            <div className="flex justify-between items-center gap-3">
              <p className="text-sm text-slate-500">{expenses.length} expense{expenses.length !== 1 ? 's' : ''}</p>
              <div className="flex items-center gap-2">
                {expenses.length === 0 ? (
                  <button type="button" onClick={() => handleGenerateExpenses(false)} disabled={expenseGenerating}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50">
                    {expenseGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Generate Line Items
                  </button>
                ) : (
                  <button type="button" onClick={() => handleGenerateExpenses(true)} disabled={expenseGenerating}
                    title="Delete all existing expenses and regenerate from budget template"
                    className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 text-slate-600 text-sm rounded-lg hover:bg-slate-50 disabled:opacity-50">
                    {expenseGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Regenerate
                  </button>
                )}
                <button type="button" onClick={() => setShowAddExpense(v => !v)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
                  <Plus className="w-4 h-4" />{showAddExpense ? 'Cancel' : 'Add Expense'}
                </button>
              </div>
            </div>
            {generateError && (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                <XCircle className="w-4 h-4 shrink-0" />{generateError}
              </div>
            )}
            {showAddExpense && (
              <form onSubmit={handleAddExpense} className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
                <h3 className="text-sm font-bold text-slate-900">New Expense</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase mb-1 text-slate-500">Category</label>
                    <select title="Expense category" value={expenseForm.category} onChange={e => setExpenseForm(f => ({ ...f, category: e.target.value }))} className="w-full px-3 py-2 border rounded-lg text-sm">
                      {['labor','equipment','locations','post_production','travel','catering','legal','insurance','visual_effects','other'].map(c => (
                        <option key={c} value={c}>{capitalize(c)}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase mb-1 text-slate-500">Amount ($)</label>
                    <input type="number" min="0.01" step="0.01" required value={expenseForm.amount} onChange={e => setExpenseForm(f => ({ ...f, amount: e.target.value }))} placeholder="0.00" className="w-full px-3 py-2 border rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase mb-1 text-slate-500">Description</label>
                    <input type="text" required value={expenseForm.description} onChange={e => setExpenseForm(f => ({ ...f, description: e.target.value }))} placeholder="e.g. Camera rental" className="w-full px-3 py-2 border rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase mb-1 text-slate-500">Date</label>
                    <input type="date" required title="Expense date" value={expenseForm.expenseDate} onChange={e => setExpenseForm(f => ({ ...f, expenseDate: e.target.value }))} className="w-full px-3 py-2 border rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase mb-1 text-slate-500">Vendor (optional)</label>
                    <input type="text" value={expenseForm.vendorName} onChange={e => setExpenseForm(f => ({ ...f, vendorName: e.target.value }))} placeholder="Vendor name" className="w-full px-3 py-2 border rounded-lg text-sm" />
                  </div>
                  <div className="flex items-end pb-1">
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <input type="checkbox" checked={expenseForm.isQualifying} onChange={e => setExpenseForm(f => ({ ...f, isQualifying: e.target.checked }))} className="w-4 h-4 rounded" />
                      <span className="font-medium text-slate-700">Qualifying expense</span>
                    </label>
                  </div>
                </div>
                <div className="flex justify-end gap-3">
                  <button type="button" onClick={() => setShowAddExpense(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
                  <button type="submit" disabled={expenseSaving} className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm rounded-lg disabled:opacity-50">
                    {expenseSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}Save Expense
                  </button>
                </div>
              </form>
            )}
            {expensesLoading ? (
              <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-blue-500" /></div>
            ) : expenses.length === 0 ? (
              <div className="bg-white rounded-xl border p-16 text-center">
                <DollarSign className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-700 font-semibold">No expenses yet</p>
                <p className="text-slate-400 text-sm">Click "Add Expense" to log your first line item.</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b">
                    <tr>{['Date','Category','Description','Vendor','Amount','Qualifying',''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {expenses.map(exp => (
                      <tr key={exp.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-slate-500">{exp.expenseDate?.split('T')[0]}</td>
                        <td className="px-4 py-3"><span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">{capitalize(exp.category)}</span></td>
                        <td className="px-4 py-3 font-medium text-slate-900">{exp.description}</td>
                        <td className="px-4 py-3 text-slate-500">{exp.vendorName || 'â€”'}</td>
                        <td className="px-4 py-3 font-semibold text-slate-900">{fmt(exp.amount)}</td>
                        <td className="px-4 py-3">{exp.isQualifying ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <XCircle className="w-4 h-4 text-slate-300" />}</td>
                        <td className="px-4 py-3">
                          <button type="button" title="Edit expense" onClick={() => { setEditingExpenseId(exp.id); setEditExpenseForm({ description: exp.description, amount: String(exp.amount), isQualifying: exp.isQualifying, vendorName: exp.vendorName || '', category: exp.category }); }} className="text-slate-300 hover:text-blue-500 transition-colors mr-2"><Pencil className="w-4 h-4" /></button><button type="button" title="Delete expense" onClick={() => handleDeleteExpense(exp.id)} className="text-slate-300 hover:text-red-500 transition-colors"><Trash2 className="w-4 h-4" /></button>
                        </td>
                      {editingExpenseId === exp.id && (
                        <tr>
                          <td colSpan={7} className="px-4 py-2 bg-blue-50 border-t">
                            <div className="flex items-center gap-2 flex-wrap">
                              <input className="border rounded px-2 py-1 text-sm w-48" value={editExpenseForm.description} onChange={e => setEditExpenseForm(f => ({...f, description: e.target.value}))} placeholder="Description" />
                              <input type="number" className="border rounded px-2 py-1 text-sm w-28" value={editExpenseForm.amount} onChange={e => setEditExpenseForm(f => ({...f, amount: e.target.value}))} placeholder="Amount" />
                              <input className="border rounded px-2 py-1 text-sm w-36" value={editExpenseForm.vendorName} onChange={e => setEditExpenseForm(f => ({...f, vendorName: e.target.value}))} placeholder="Vendor" />
                              <label className="flex items-center gap-1 text-sm cursor-pointer"><input type="checkbox" checked={editExpenseForm.isQualifying} onChange={e => setEditExpenseForm(f => ({...f, isQualifying: e.target.checked}))} /> Qualifying</label>
                              <button onClick={() => handleEditExpenseSave(exp.id)} className="px-3 py-1 bg-blue-600 text-white rounded text-sm">Save</button>
                              <button onClick={() => setEditingExpenseId(null)} className="px-3 py-1 border rounded text-sm">Cancel</button>
                            </div>
                          </td>
                        </tr>
                      )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Compliance Tab */}
        {tab === 'compliance' && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              {compliance && compliance.total > 0 && <p className="text-sm text-slate-500"><span className="font-bold">{compliance.complete}</span> of <span className="font-bold">{compliance.total}</span> items complete{compliance.waived > 0 && ` Â· ${compliance.waived} waived`}</p>}
              <div className="flex gap-2">
                {compliance && compliance.total > 0 && <button onClick={loadCompliance} className="flex items-center gap-1.5 px-3 py-1.5 text-xs border rounded-lg"><RefreshCw className="w-3.5 h-3.5" />Refresh</button>}
                <button onClick={handleGenerateChecklist} disabled={compLoading} className="flex items-center gap-1.5 px-4 py-1.5 text-xs bg-blue-600 text-white rounded-lg">{compLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}{compliance ? 'Regenerate' : 'Generate'} Checklist</button>
              </div>
            </div>
            {compliance && compliance.total > 0 && <div className="bg-white rounded-xl border p-5"><div className="flex justify-between text-sm mb-2"><span className="font-semibold">Overall Completion</span><span>{compliance.pct}%</span></div><progress value={compliance.pct} max={100} className="w-full h-3 rounded-full" /><div className="flex gap-4 mt-2.5 text-xs"><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-500" /> Complete ({compliance.complete})</span><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-slate-200" /> Pending ({compliance.pending})</span>{compliance.waived > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-400" /> Waived ({compliance.waived})</span>}</div></div>}
            {(compliance?.items?.length ?? 0) > 0 && Object.entries((compliance!.items ?? []).reduce<Record<string, ComplianceItem[]>>((acc, i) => { (acc[i.category] ||= []).push(i); return acc; }, {})).sort(([a], [b]) => a.localeCompare(b)).map(([cat, items]) => (
              <div key={cat} className="bg-white rounded-xl border overflow-hidden"><div className="flex justify-between px-6 py-3.5 border-b bg-slate-50"><h3 className="text-xs font-bold uppercase">{capitalize(cat)}</h3><span className="text-xs">{items.filter(i => i.status === 'complete').length}/{items.length} complete</span></div><div className="divide-y divide-slate-50">{items.map(item => { const cfg = COMPLIANCE_STATUS_CONFIG[item.status]; return (<div key={item.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-slate-50"><button onClick={() => cycleStatus(item)} className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${item.status === 'complete' ? 'bg-emerald-500 border-emerald-500' : item.status === 'waived' ? 'bg-amber-400 border-amber-400' : item.status === 'na' ? 'bg-slate-200 border-slate-200' : 'border-slate-300'}`}>{item.status === 'complete' && <CheckCircle2 className="w-3 h-3 text-white" />}{item.status === 'waived' && <XCircle className="w-3 h-3 text-white" />}</button><span className={`text-sm flex-1 ${item.status === 'complete' ? 'line-through text-slate-400' : ''}`}>{item.label}</span><span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${cfg.cls}`}>{cfg.label}</span></div>); })}</div></div>
            ))}
            {(!compliance || compliance.total === 0) && !compLoading && <div className="bg-white rounded-xl border p-16 text-center"><ClipboardCheck className="w-8 h-8 text-slate-300 mx-auto mb-3" /><p className="text-slate-700 font-semibold">No checklist yet</p><p className="text-slate-400 text-sm">Click "Generate Checklist" to create compliance items.</p></div>}
            {compLoading && <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-blue-500" /></div>}
          </div>
        )}

        {/* Calculator Tab */}
        {tab === 'calculator' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border p-6"><h2 className="text-sm font-bold mb-4">Incentive Calculator</h2><div className="flex gap-4 items-end"><div className="flex-1"><label className="block text-xs font-semibold uppercase mb-2">Jurisdiction</label><select value={calcJurId} onChange={e => { setCalcJurId(e.target.value); setCalcResult(null); }} className="w-full px-3.5 py-2.5 border rounded-lg">{jurisdictions.map(j => <option key={j.id} value={j.id}>{j.name} ({j.code}){j.id === production.jurisdictionId ? ' â˜… primary' : ''}</option>)}</select></div><button onClick={handleCalculate} disabled={!calcJurId || calcLoading} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg">{calcLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}{calcLoading ? 'Calculatingâ€¦' : 'Calculate'}</button></div>{calcError && <p className="text-red-600 text-sm mt-3">{calcError}</p>}</div>
            {calcResult && (() => { const sel = jurisdictions.find(j => j.id === calcResult.jurisdiction_id); const rate = calcResult.qualified_expenses > 0 ? (calcResult.incentive_amount / calcResult.qualified_expenses) * 100 : 0; return (<div className="space-y-4"><div className="grid grid-cols-4 gap-4"><StatCard label="Total Expenses" value={fmt(calcResult.total_expenses)} /><StatCard label="Qualified Expenses" value={fmt(calcResult.qualified_expenses)} sub={calcResult.total_expenses ? fmtPct((calcResult.qualified_expenses / calcResult.total_expenses) * 100) : undefined} /><StatCard label="Estimated Credit" value={fmt(calcResult.incentive_amount)} accent /><StatCard label="Effective Rate" value={fmtPct(calcResult.effective_rate * 100)} /></div><div className="bg-white rounded-xl border p-6"><h3 className="text-sm font-bold mb-4">Summary â€” {sel?.name}</h3><dl className="space-y-3">{([['Production', production.title], ['Jurisdiction', sel ? `${sel.name} (${sel.code})` : 'â€”'], ['Total Expenses', fmt(calcResult.total_expenses)], ['Qualified Expenses', fmt(calcResult.qualified_expenses)], ['Qualification Rate', fmtPct((calcResult.qualified_expenses / calcResult.total_expenses) * 100)], ['Credit Rate', fmtPct(rate)], ['Estimated Credit', fmt(calcResult.incentive_amount)], ['Effective Rate', fmtPct(calcResult.effective_rate * 100)]] as [string, string][]).map(([l, v]) => <div key={l} className="flex justify-between py-2 border-b"><dt className="text-slate-500">{l}</dt><dd className="font-semibold">{v}</dd></div>)}</dl></div></div>); })()}
            {!calcResult && !calcLoading && <div className="bg-white rounded-xl border p-16 text-center"><TrendingUp className="w-8 h-8 text-slate-300 mx-auto mb-3" /><p className="text-slate-700 font-semibold">Select a jurisdiction and calculate</p></div>}
          </div>
        )}

        {/* Rules Tab */}
        {tab === 'rules' && (
          <div className="space-y-4">
            {rules.length === 0 ? <div className="bg-white rounded-xl border p-16 text-center"><BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-3" /><p className="text-slate-700 font-semibold">No rules found</p></div> : <>
              <p className="text-sm text-slate-500">{rules.length} active rule(s) for {jur?.name}</p>
              {rules.map(rule => (<div key={rule.id} className="bg-white rounded-xl border p-6"><div className="flex justify-between mb-3"><div><h3 className="text-sm font-bold">{rule.ruleName}</h3><p className="text-xs text-slate-500">{rule.ruleCode}</p></div>{rule.percentage && <span className="text-2xl font-bold text-blue-600">{rule.percentage}%</span>}{rule.fixedAmount && <span className="text-2xl font-bold text-blue-600">{fmt(rule.fixedAmount)}</span>}</div><div className="grid grid-cols-4 gap-4 text-xs mb-4">{rule.minSpend && <div><p className="text-slate-400">Min Spend</p><p className="font-semibold">{fmt(rule.minSpend)}</p></div>}{rule.maxCredit && <div><p className="text-slate-400">Max Credit</p><p className="font-semibold">{fmt(rule.maxCredit)}</p></div>}<div><p className="text-slate-400">Effective</p><p className="font-semibold">{rule.effectiveDate?.split('T')[0]}</p></div>{rule.expirationDate && <div><p className="text-slate-400">Expires</p><p className="font-semibold text-amber-700">{rule.expirationDate.split('T')[0]}</p></div>}</div><div className="flex flex-wrap gap-2">{rule.eligibleExpenses?.map(e => <span key={e} className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs">{capitalize(e)}</span>)}</div></div>))}
            </>}
          </div>
        )}

      

        {/* Intelligence Tab */}
        {tab === 'signals' && (
          <SignalDashboard productionId={production.id} token={localStorage.getItem('sceneiq_token') || ''} />
        )}
      </div>
    </div>
  );
}









