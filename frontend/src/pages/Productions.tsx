import { useState, useEffect, useMemo } from 'react';
import { Search, Plus, Filter, ChevronRight, X, Loader2, Trash2, Pencil, ExternalLink } from 'lucide-react';
import type { Production, Jurisdiction } from '../types';
import api from '../api';
import ProductionDetail from './ProductionDetail';

// ─── Constants ────────────────────────────────────────────────────────────────

type StatusKey = 'planning' | 'pre_production' | 'production' | 'post_production' | 'completed';

const STATUS_OPTIONS: { value: StatusKey; label: string }[] = [
  { value: 'planning',        label: 'Planning' },
  { value: 'pre_production',  label: 'Pre-Production' },
  { value: 'production',      label: 'Production' },
  { value: 'post_production', label: 'Post-Production' },
  { value: 'completed',       label: 'Completed' },
];

const PROD_TYPES = [
  { value: 'feature',      label: 'Feature Film' },
  { value: 'tv_series',    label: 'TV Series' },
  { value: 'commercial',   label: 'Commercial' },
  { value: 'documentary',  label: 'Documentary' },
];

const STATUS_COLORS: Record<string, string> = {
  planning:        'bg-blue-100 text-blue-800',
  pre_production:  'bg-violet-100 text-violet-800',
  production:      'bg-green-100 text-green-800',
  post_production: 'bg-amber-100 text-amber-800',
  completed:       'bg-slate-100 text-slate-700',
};

const EMPTY_FORM = {
  title: '',
  productionType: 'feature',
  productionCompany: '',
  budgetTotal: '',
  episodeCount: '',
  startDate: '',
  jurisdictionId: '',
  status: 'planning' as StatusKey,
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function Productions() {
  const [productions, setProductions] = useState<Production[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | StatusKey>('all');
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<Record<keyof typeof EMPTY_FORM, string>>>({});
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editProduction, setEditProduction] = useState<Production | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editErrors, setEditErrors] = useState<Partial<Record<keyof typeof EMPTY_FORM, string>>>({});
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    Promise.all([api.productions.list(), api.jurisdictions.list()])
      .then(([prods, jurs]) => { setProductions(prods); setJurisdictions(jurs); })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  // Memoized jurisdiction name lookup — O(1) vs O(n) per card
  const jurMap = useMemo(() =>
    new Map(jurisdictions.map(j => [j.id, j.name])),
  [jurisdictions]);

  const jurName = (id: string) => jurMap.get(id) ?? '—';

  // Memoized filtered list
  const filtered = useMemo(() => productions.filter(p => {
    const matchSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchStatus = filterStatus === 'all' || p.status === filterStatus;
    return matchSearch && matchStatus;
  }), [productions, searchTerm, filterStatus]);

  // ── Validation ──────────────────────────────────────────────────────────────

  function validate() {
    const e: Partial<Record<keyof typeof EMPTY_FORM, string>> = {};
    if (!form.title.trim())           e.title           = 'Title is required';
    if (!form.productionCompany.trim()) e.productionCompany = 'Company is required';
    if (!form.startDate)              e.startDate       = 'Start date is required';
    const b = Number(form.budgetTotal);
    if (!form.budgetTotal || isNaN(b) || b <= 0) e.budgetTotal = 'Enter a valid budget';
    if (form.episodeCount) {
      const n = Number(form.episodeCount);
      if (!Number.isInteger(n) || n < 1) e.episodeCount = 'Enter a whole number';
    }
    return e;
  }

  // ── Submit ──────────────────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setSubmitting(true);
    try {
      const created = await api.productions.create({
        title:             form.title.trim(),
        productionType:    form.productionType,
        productionCompany: form.productionCompany.trim(),
        budgetTotal:       Number(form.budgetTotal),
        episodeCount:      form.episodeCount ? Number(form.episodeCount) : null,
        startDate:         form.startDate,
        jurisdictionId:    form.jurisdictionId || '',
        status:            form.status,
      });
      setProductions(prev => [created, ...prev]);
      setForm(EMPTY_FORM);
      setErrors({});
      setShowModal(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create production';
      setErrors({ title: msg });
    } finally {
      setSubmitting(false);
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────────

  async function handleDelete(id: string) {
    setDeleteId(id);
    try {
      await api.productions.delete(id);
      setProductions(prev => prev.filter(p => p.id !== id));
    } catch {
      // silent — production stays in list
    } finally {
      setDeleteId(null);
    }
  }

  function handleClose() {
    setShowModal(false);
    setForm(EMPTY_FORM);
    setErrors({});
  }

  function handleEditOpen(e: React.MouseEvent, p: Production) {
    e.stopPropagation();
    setEditProduction(p);
    setEditForm({
      title:             p.title,
      productionType:    p.productionType,
      productionCompany: p.productionCompany,
      budgetTotal:       String(p.budgetTotal),
      episodeCount:      p.episodeCount != null ? String(p.episodeCount) : '',
      startDate:         p.startDate?.split('T')[0] ?? '',
      jurisdictionId:    p.jurisdictionId ?? '',
      status:            p.status as StatusKey,
    });
    setEditErrors({});
  }

  function handleEditClose() {
    setEditProduction(null);
    setEditForm(EMPTY_FORM);
    setEditErrors({});
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editProduction) return;
    const errs: Partial<Record<keyof typeof EMPTY_FORM, string>> = {};
    if (!editForm.title.trim())             errs.title           = 'Title is required';
    if (!editForm.productionCompany.trim()) errs.productionCompany = 'Company is required';
    if (!editForm.startDate)                errs.startDate       = 'Start date is required';
    const b = Number(editForm.budgetTotal);
    if (!editForm.budgetTotal || isNaN(b) || b <= 0) errs.budgetTotal = 'Enter a valid budget';
    if (editForm.episodeCount) {
      const n = Number(editForm.episodeCount);
      if (!Number.isInteger(n) || n < 1) errs.episodeCount = 'Enter a whole number';
    }
    if (Object.keys(errs).length) { setEditErrors(errs); return; }

    setUpdating(true);
    try {
      const updated = await api.productions.update(editProduction.id, {
        title:             editForm.title.trim(),
        productionType:    editForm.productionType,
        productionCompany: editForm.productionCompany.trim(),
        budgetTotal:       Number(editForm.budgetTotal),
        episodeCount:      editForm.episodeCount ? Number(editForm.episodeCount) : null,
        startDate:         editForm.startDate,
        jurisdictionId:    editForm.jurisdictionId || '',
        status:            editForm.status,
      });
      setProductions(prev => prev.map(p => p.id === editProduction.id ? updated : p));
      handleEditClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update production';
      setEditErrors({ title: msg });
    } finally {
      setUpdating(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (selectedId) {
    return <ProductionDetail productionId={selectedId} onBack={() => setSelectedId(null)} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-8 py-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-[28px] font-bold text-slate-900">Productions</h1>
            <p className="text-slate-500 mt-1 text-[15px]">Manage and track all film productions.</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
          >
            <Plus className="w-4 h-4" />
            New Production
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-8 max-w-6xl mx-auto">
        {/* Search and Filter */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search productions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <button type="button" className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors text-slate-700 font-medium text-sm">
            <Filter className="w-4 h-4" />
            Filter
          </button>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {(['all', ...STATUS_OPTIONS.map(s => s.value)] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors text-sm ${
                filterStatus === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-700 border border-slate-300 hover:border-slate-400'
              }`}
            >
              {status === 'all' ? 'All' : STATUS_OPTIONS.find(s => s.value === status)?.label ?? status}
            </button>
          ))}
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        )}

        {/* Productions List */}
        {!isLoading && (
          <div className="space-y-4">
            {filtered.map((p) => (
              <div
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow group cursor-pointer"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                      <h3 className="text-base font-bold text-slate-900">{p.title}</h3>
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${STATUS_COLORS[p.status] ?? 'bg-slate-100 text-slate-700'}`}>
                        {STATUS_OPTIONS.find(s => s.value === p.status)?.label ?? p.status}
                      </span>
                      {p.episodeCount != null && (
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                          {p.episodeCount} eps
                        </span>
                      )}
                    </div>
                    <p className="text-slate-500 text-sm">
                      {jurName(p.jurisdictionId)} • {p.productionCompany} • Started {p.startDate?.split('T')[0]}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    {/* View Expenses button for "The Wild World" */}
                    {p.title === 'The Wild World' && (
                      <a
                        href="http://127.0.0.1:8001/static/budget_demo.html"
                        target="_blank"
                        rel="noopener noreferrer"
                        title="View budget line items"
                        className="text-slate-300 hover:text-blue-500 transition-colors"
                        onClick={e => e.stopPropagation()}
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={e => handleEditOpen(e, p)}
                      title="Edit production"
                      aria-label="Edit production"
                      className="text-slate-300 hover:text-blue-500 transition-colors"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); handleDelete(p.id); }}
                      disabled={deleteId === p.id}
                      title="Delete production"
                      aria-label="Delete production"
                      className="text-slate-300 hover:text-red-500 transition-colors disabled:opacity-50"
                    >
                      {deleteId === p.id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />
                      }
                    </button>
                    <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-slate-600 transition-colors" />
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <p className="text-slate-500 text-xs font-medium mb-0.5">Budget</p>
                    <p className="text-base font-bold text-slate-900">${(p.budgetTotal / 1_000_000).toFixed(1)}M</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs font-medium mb-0.5">Type</p>
                    <p className="text-base font-bold text-slate-900">{PROD_TYPES.find(t => t.value === p.productionType)?.label ?? p.productionType}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs font-medium mb-0.5">Episodes</p>
                    <p className="text-base font-bold text-slate-900">{p.episodeCount ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs font-medium mb-0.5">Jurisdiction</p>
                    <p className="text-base font-bold text-slate-900">{jurName(p.jurisdictionId)}</p>
                  </div>
                </div>
              </div>
            ))}

            {filtered.length === 0 && !isLoading && (
              <div className="bg-white rounded-xl border border-slate-200 p-16 text-center">
                {productions.length === 0 ? (
                  <>
                    <p className="text-slate-700 font-semibold mb-1">No productions yet</p>
                    <p className="text-slate-500 text-sm">Click "New Production" to add your first production.</p>
                  </>
                ) : (
                  <p className="text-slate-500 text-sm">No productions match your filters.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Edit Production Modal (unchanged) */}
      {editProduction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleEditClose} />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Edit Production</h2>
                <p className="text-slate-500 text-sm mt-0.5">{editProduction.title}</p>
              </div>
              <button type="button" onClick={handleEditClose} title="Close" aria-label="Close" className="text-slate-400 hover:text-slate-600 transition-colors mt-0.5">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Production Title <span className="text-red-500">*</span></label>
                <input type="text" value={editForm.title}
                  onChange={e => { setEditForm(f => ({ ...f, title: e.target.value })); setEditErrors(er => ({ ...er, title: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${editErrors.title ? 'border-red-400' : 'border-slate-300'}`}
                  autoFocus />
                {editErrors.title && <p className="text-red-500 text-xs mt-1">{editErrors.title}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Production Type</label>
                <select value={editForm.productionType} onChange={e => setEditForm(f => ({ ...f, productionType: e.target.value }))}
                  title="Production type" aria-label="Production type"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
                  {PROD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Production Company <span className="text-red-500">*</span></label>
                <input type="text" title="Production company" placeholder="e.g. Horizon Films LLC" value={editForm.productionCompany}
                  onChange={e => { setEditForm(f => ({ ...f, productionCompany: e.target.value })); setEditErrors(er => ({ ...er, productionCompany: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${editErrors.productionCompany ? 'border-red-400' : 'border-slate-300'}`} />
                {editErrors.productionCompany && <p className="text-red-500 text-xs mt-1">{editErrors.productionCompany}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Total Budget (USD) <span className="text-red-500">*</span></label>
                <div className="relative">
                  <span className="absolute left-3.5 top-2.5 text-slate-400 text-sm select-none">$</span>
                  <input type="number" title="Total budget" placeholder="5000000" min="1" value={editForm.budgetTotal}
                    onChange={e => { setEditForm(f => ({ ...f, budgetTotal: e.target.value })); setEditErrors(er => ({ ...er, budgetTotal: undefined })); }}
                    className={`w-full pl-7 pr-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${editErrors.budgetTotal ? 'border-red-400' : 'border-slate-300'}`} />
                </div>
                {editErrors.budgetTotal && <p className="text-red-500 text-xs mt-1">{editErrors.budgetTotal}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Episode Count <span className="text-slate-400 text-xs">(optional — for TV series)</span>
                </label>
                <input type="number" title="Episode count" placeholder="e.g. 6" min="1" step="1" value={editForm.episodeCount}
                  onChange={e => { setEditForm(f => ({ ...f, episodeCount: e.target.value })); setEditErrors(er => ({ ...er, episodeCount: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${editErrors.episodeCount ? 'border-red-400' : 'border-slate-300'}`} />
                {editErrors.episodeCount && <p className="text-red-500 text-xs mt-1">{editErrors.episodeCount}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Start Date <span className="text-red-500">*</span></label>
                <input type="date" title="Start date" value={editForm.startDate}
                  onChange={e => { setEditForm(f => ({ ...f, startDate: e.target.value })); setEditErrors(er => ({ ...er, startDate: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${editErrors.startDate ? 'border-red-400' : 'border-slate-300'}`} />
                {editErrors.startDate && <p className="text-red-500 text-xs mt-1">{editErrors.startDate}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Jurisdiction</label>
                <select value={editForm.jurisdictionId} onChange={e => setEditForm(f => ({ ...f, jurisdictionId: e.target.value }))}
                  title="Jurisdiction" aria-label="Jurisdiction"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-700">
                  <option value="">No jurisdiction</option>
                  {jurisdictions.map(j => <option key={j.id} value={j.id}>{j.name} ({j.country})</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Status</label>
                <select value={editForm.status} onChange={e => setEditForm(f => ({ ...f, status: e.target.value as StatusKey }))}
                  title="Status" aria-label="Status"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
                  {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={handleEditClose}
                  className="flex-1 py-2.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={updating}
                  className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-60 flex items-center justify-center gap-2">
                  {updating && <Loader2 className="w-4 h-4 animate-spin" />}
                  {updating ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Production Modal (unchanged) */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleClose} />

          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-slate-900">New Production</h2>
                <p className="text-slate-500 text-sm mt-0.5">Add a new film production to track.</p>
              </div>
              <button type="button" onClick={handleClose} title="Close" aria-label="Close" className="text-slate-400 hover:text-slate-600 transition-colors mt-0.5">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Production Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. The Silent Horizon"
                  value={form.title}
                  onChange={e => { setForm(f => ({ ...f, title: e.target.value })); setErrors(er => ({ ...er, title: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.title ? 'border-red-400' : 'border-slate-300'}`}
                  autoFocus
                />
                {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
              </div>

              {/* Production Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Production Type <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.productionType}
                  onChange={e => setForm(f => ({ ...f, productionType: e.target.value }))}
                  title="Production type"
                  aria-label="Production type"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  {PROD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>

              {/* Production Company */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Production Company <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Horizon Films LLC"
                  value={form.productionCompany}
                  onChange={e => { setForm(f => ({ ...f, productionCompany: e.target.value })); setErrors(er => ({ ...er, productionCompany: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.productionCompany ? 'border-red-400' : 'border-slate-300'}`}
                />
                {errors.productionCompany && <p className="text-red-500 text-xs mt-1">{errors.productionCompany}</p>}
              </div>

              {/* Budget */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Total Budget (USD) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-2.5 text-slate-400 text-sm select-none">$</span>
                  <input
                    type="number"
                    placeholder="5000000"
                    min="1"
                    value={form.budgetTotal}
                    onChange={e => { setForm(f => ({ ...f, budgetTotal: e.target.value })); setErrors(er => ({ ...er, budgetTotal: undefined })); }}
                    className={`w-full pl-7 pr-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.budgetTotal ? 'border-red-400' : 'border-slate-300'}`}
                  />
                </div>
                {errors.budgetTotal && <p className="text-red-500 text-xs mt-1">{errors.budgetTotal}</p>}
              </div>

              {/* Episode Count */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Episode Count <span className="text-slate-400 text-xs">(optional — for TV series)</span>
                </label>
                <input
                  type="number"
                  title="Episode count"
                  placeholder="e.g. 6"
                  min="1"
                  step="1"
                  value={form.episodeCount}
                  onChange={e => { setForm(f => ({ ...f, episodeCount: e.target.value })); setErrors(er => ({ ...er, episodeCount: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.episodeCount ? 'border-red-400' : 'border-slate-300'}`}
                />
                {errors.episodeCount && <p className="text-red-500 text-xs mt-1">{errors.episodeCount}</p>}
              </div>

              {/* Start Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Start Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  title="Start date"
                  value={form.startDate}
                  onChange={e => { setForm(f => ({ ...f, startDate: e.target.value })); setErrors(er => ({ ...er, startDate: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.startDate ? 'border-red-400' : 'border-slate-300'}`}
                />
                {errors.startDate && <p className="text-red-500 text-xs mt-1">{errors.startDate}</p>}
              </div>

              {/* Jurisdiction */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Jurisdiction</label>
                <select
                  value={form.jurisdictionId}
                  onChange={e => setForm(f => ({ ...f, jurisdictionId: e.target.value }))}
                  title="Jurisdiction"
                  aria-label="Jurisdiction"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-700"
                >
                  <option value="">Select jurisdiction (optional)</option>
                  {jurisdictions.map(j => (
                    <option key={j.id} value={j.id}>{j.name} ({j.country})</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Status</label>
                <select
                  value={form.status}
                  onChange={e => setForm(f => ({ ...f, status: e.target.value as StatusKey }))}
                  title="Status"
                  aria-label="Status"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex-1 py-2.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {submitting ? 'Creating…' : 'Create Production'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}