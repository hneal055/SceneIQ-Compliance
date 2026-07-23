import USJurisdictionMap from '../components/USJurisdictionMap';
import { useState, useEffect, useMemo } from 'react';
import { Search, RefreshCw, Bookmark, ChevronDown, X, ExternalLink, CheckCircle, Send, Loader2 } from 'lucide-react';
import type { Jurisdiction, IncentiveRule, MonitoringEvent } from '../types';
import api from '../api';
import JurisdictionDetail from '../components/JurisdictionDetail';

// --- Helpers -----------------------------------------------------------------

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days  = Math.floor(diff / 86_400_000);
  if (mins  < 60)  return `${mins}m ago`;
  if (hours < 24)  return `${hours}h ago`;
  return `${days}d ago`;
}

function capitalize(s: string) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

// --- Sub-components ----------------------------------------------------------

function FilterDropdown({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:border-slate-300 transition-colors shadow-sm"
      >
        {value}
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute top-full mt-1 left-0 bg-white border border-slate-200 rounded-lg shadow-lg z-20 min-w-[160px] py-1">
            {options.map(opt => (
              <button
                key={opt}
                type="button"
                onClick={() => { onChange(opt); setOpen(false); }}
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${value === opt ? 'text-blue-600 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`}
              >
                {opt}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-slate-900 text-white px-5 py-3 rounded-xl shadow-xl text-sm font-medium">
      <span>{message}</span>
      <button type="button" onClick={onClose} title="Dismiss" aria-label="Dismiss notification" className="text-slate-400 hover:text-white transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// --- Concierge modal ---------------------------------------------------------

const INQUIRY_TYPES = [
  'Custom jurisdiction application',
  'Incentive eligibility review',
  'Multi-jurisdiction strategy',
  'Document preparation assistance',
  'Other',
];

function ConciergeModal({ onClose }: { onClose: () => void }) {
  const [form, setForm]        = useState({ name: '', email: '', inquiry: INQUIRY_TYPES[0], message: '' });
  const [submitted, setSubmit] = useState(false);
  const [errors, setErrors]    = useState<{ name?: string; email?: string; message?: string }>({});

  function validate() {
    const e: typeof errors = {};
    if (!form.name.trim())                               e.name    = 'Name is required';
    if (!form.email.trim() || !form.email.includes('@')) e.email   = 'Valid email is required';
    if (!form.message.trim())                            e.message = 'Please describe your inquiry';
    return e;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSubmit(true);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">

        <div className="flex items-start justify-between px-7 pt-7 pb-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-100 rounded-xl flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Contact Concierge</h2>
              <p className="text-slate-500 text-xs mt-0.5">SceneIQ specialist team - typically replies in 2h</p>
            </div>
          </div>
          <button type="button" onClick={onClose} title="Close" aria-label="Close" className="text-slate-400 hover:text-slate-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {submitted ? (
          <div className="px-7 py-10 flex flex-col items-center text-center">
            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="w-7 h-7 text-emerald-600" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1.5">Request Received</h3>
            <p className="text-slate-500 text-sm max-w-xs">
              A SceneIQ specialist will review your inquiry and reach out within 2 business hours.
            </p>
            <div className="mt-6 w-full bg-slate-50 rounded-xl p-4 text-left space-y-1.5 border border-slate-100">
              <p className="text-xs text-slate-500"><span className="font-semibold text-slate-700">Name:</span> {form.name}</p>
              <p className="text-xs text-slate-500"><span className="font-semibold text-slate-700">Email:</span> {form.email}</p>
              <p className="text-xs text-slate-500"><span className="font-semibold text-slate-700">Topic:</span> {form.inquiry}</p>
            </div>
            <button type="button" onClick={onClose} className="mt-6 px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors">
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="px-7 py-6 space-y-4">
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3">
              <p className="text-indigo-600 text-xs leading-relaxed">
                <span className="font-bold">How this works: </span>
                Our concierge team handles custom jurisdiction research, application preparation, and multi-territory strategy.
                Submissions route to a specialist based on your inquiry type.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">Full Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  placeholder="Jane Smith"
                  value={form.name}
                  onChange={e => { setForm(f => ({ ...f, name: e.target.value })); setErrors(er => ({ ...er, name: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.name ? 'border-red-400' : 'border-slate-200'}`}
                />
                {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">Email <span className="text-red-400">*</span></label>
                <input
                  type="email"
                  placeholder="jane@studio.com"
                  value={form.email}
                  onChange={e => { setForm(f => ({ ...f, email: e.target.value })); setErrors(er => ({ ...er, email: undefined })); }}
                  className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.email ? 'border-red-400' : 'border-slate-200'}`}
                />
                {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">Inquiry Type</label>
              <select
                value={form.inquiry}
                onChange={e => setForm(f => ({ ...f, inquiry: e.target.value }))}
                title="Inquiry Type"
                aria-label="Inquiry Type"
                className="select-arrow w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
              >
                {INQUIRY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">Message <span className="text-red-400">*</span></label>
              <textarea
                rows={4}
                placeholder="Describe your production's needs, jurisdiction targets, and any specific questions..."
                value={form.message}
                onChange={e => { setForm(f => ({ ...f, message: e.target.value })); setErrors(er => ({ ...er, message: undefined })); }}
                className={`w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none ${errors.message ? 'border-red-400' : 'border-slate-200'}`}
              />
              {errors.message && <p className="text-red-500 text-xs mt-1">{errors.message}</p>}
            </div>

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
                Cancel
              </button>
              <button type="submit" className="flex-1 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2">
                <Send className="w-4 h-4" />
                Send Inquiry
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// --- Main component ----------------------------------------------------------

export default function Jurisdictions() {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [rules,         setRules]         = useState<IncentiveRule[]>([]);
  const [isLoading,     setIsLoading]     = useState(true);
  const [feedEvents,    setFeedEvents]    = useState<MonitoringEvent[]>([]);
  const [feedLoading,   setFeedLoading]   = useState(true);

  const [search,       setSearch]       = useState('');
  const [typeFilter,   setTypeFilter]   = useState('All Types');
  const [countryFilter, setCountry]     = useState('All Countries');
  const [selectedId,   setSelectedId]   = useState<string | null>(null);
  const [savedIds,     setSavedIds]     = useState<Set<string>>(new Set());
  const [toast,        setToast]        = useState<string | null>(null);
  const [showConcierge, setConcierge]   = useState(false);
  const [addedIds,     setAddedIds]     = useState<Set<string>>(new Set());

  useEffect(() => {
    Promise.all([api.jurisdictions.list(), api.incentiveRules.list()])
      .then(([jurs, rls]) => { setJurisdictions(jurs); setRules(rls); })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    api.monitoring.events.list({ limit: 10 })
      .then(res => setFeedEvents(res.events))
      .catch(() => {})
      .finally(() => setFeedLoading(false));
  }, []);

  // -- Client-side join helpers -----------------------------------------------

  function getBestRate(jId: string): number {
    return rules
      .filter(r => r.jurisdictionId === jId && r.active && r.percentage != null)
      .reduce((max, r) => Math.max(max, r.percentage ?? 0), 0);
  }

  function getMinSpend(jId: string): string {
    const r = rules.find(r => r.jurisdictionId === jId && r.active && r.minSpend != null);
    if (!r?.minSpend) return 'None';
    const v = r.minSpend;
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}k`;
    return `$${v}`;
  }

  function getCreditTypes(jId: string): string[] {
    return [...new Set(
      rules.filter(r => r.jurisdictionId === jId && r.active && r.creditType)
           .map(r => r.creditType)
    )];
  }

  const CREDIT_TYPE_STYLE: Record<string, string> = {
    refundable:     'bg-emerald-50 text-emerald-700 border-emerald-200',
    transferable:   'bg-blue-50 text-blue-700 border-blue-200',
    non_refundable: 'bg-amber-50 text-amber-700 border-amber-200',
    rebate:         'bg-violet-50 text-violet-700 border-violet-200',
    grant:          'bg-sky-50 text-sky-700 border-sky-200',
  };

  const CREDIT_TYPE_LABEL: Record<string, string> = {
    refundable:     'Refundable',
    transferable:   'Transferable',
    non_refundable: 'Non-Refundable',
    rebate:         'Cash Rebate',
    grant:          'Grant',
  };

  // -- Dynamic filter options -------------------------------------------------

  const ALL_TYPES = useMemo(() => {
    const types = Array.from(new Set(jurisdictions.map(j => capitalize(j.type)))).sort();
    return ['All Types', ...types];
  }, [jurisdictions]);

  const ALL_COUNTRIES = useMemo(() => {
    const countries = Array.from(new Set(jurisdictions.map(j => j.country))).sort();
    return ['All Countries', ...countries];
  }, [jurisdictions]);

  // -- Filtering --------------------------------------------------------------

  const filtered = useMemo(() => jurisdictions.filter(j => {
    const matchType    = typeFilter    === 'All Types'     || capitalize(j.type) === typeFilter;
    const matchCountry = countryFilter === 'All Countries' || j.country === countryFilter;
    const matchSearch  = !search.trim() ||
      j.name.toLowerCase().includes(search.toLowerCase()) ||
      j.country.toLowerCase().includes(search.toLowerCase()) ||
      j.code.toLowerCase().includes(search.toLowerCase());
    return matchType && matchCountry && matchSearch;
  }), [jurisdictions, search, typeFilter, countryFilter]);

  // -- Handlers ---------------------------------------------------------------

  function showToast(msg: string) { setToast(msg); setTimeout(() => setToast(null), 3000); }

  function toggleSave(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setSavedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  function handleAddHint(name: string, e: React.MouseEvent) {
    e.stopPropagation();
    setAddedIds(prev => new Set(prev).add(name));
    setTimeout(() => setAddedIds(prev => { const n = new Set(prev); n.delete(name); return n; }), 2500);
    showToast(`Go to Productions to create a production in ${name}`);
  }

  function handleReview(j: Jurisdiction, e: React.MouseEvent) {
    e.stopPropagation();
    window.open(j.website ?? '#', '_blank', 'noopener,noreferrer');
  }

  function handleRefresh() {
    setIsLoading(true);
    Promise.all([api.jurisdictions.list(), api.incentiveRules.list()])
      .then(([jurs, rls]) => { setJurisdictions(jurs); setRules(rls); showToast('Jurisdiction data refreshed'); })
      .catch(() => showToast('Refresh failed'))
      .finally(() => setIsLoading(false));
  }

  const selectedJur = selectedId ? jurisdictions.find(j => j.id === selectedId) ?? null : null;

  // Full detail view when a jurisdiction is selected
  if (selectedJur) {
    return (
      <JurisdictionDetail
        code={selectedJur.code}
        name={selectedJur.name}
        onBack={() => setSelectedId(null)}
        onNavigate={(code) => {
          const target = jurisdictions.find(j => j.code === code);
          if (target) setSelectedId(target.id);
        }}
      />
    );
  }

  return (
    <div className="flex gap-6 h-full min-h-0">

      {/* -- Left panel ---------------------------------------------------- */}
      <div className="w-72 shrink-0 flex flex-col gap-4">

        {/* Regulatory Feed */}
        <div className="bg-[#13151a] rounded-2xl overflow-hidden flex flex-col">
          <div className="flex items-center gap-2.5 px-5 py-4 border-b border-white/8">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
            </span>
            <span className="text-white text-xs font-bold tracking-widest uppercase">Regulatory Feed</span>
          </div>

          <div className="divide-y divide-white/8">
            {feedLoading && (
              <div className="px-5 py-6 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
              </div>
            )}
            {!feedLoading && feedEvents.length === 0 && (
              <div className="px-5 py-4 text-slate-500 text-xs text-center">No events yet.</div>
            )}
            {!feedLoading && feedEvents.map(event => (
              <div key={event.id} className={`px-5 py-4 hover:bg-white/4 transition-colors group ${!event.isRead ? 'border-l-2 border-blue-500' : ''}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <a
                    href={event.url ?? event.source?.url ?? '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-400 text-xs font-semibold hover:text-blue-300 transition-colors"
                    onClick={e => {
                      e.stopPropagation();
                      if (!event.isRead) {
                        api.monitoring.events.markRead(event.id)
                          .then(() => setFeedEvents(prev => prev.map(ev => ev.id === event.id ? { ...ev, isRead: true } : ev)))
                          .catch(() => {});
                      }
                    }}
                  >
                    {event.source?.name ?? 'Regulatory Update'}
                    <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                  <span className="text-slate-500 text-xs">{timeAgo(event.publishedAt ?? event.createdAt)}</span>
                </div>
                <p className="text-slate-400 text-xs leading-relaxed">{event.summary ?? event.title}</p>
              </div>
            ))}
          </div>

          <div className="px-5 py-3 text-center">
            <span className="text-slate-600 text-[11px] tracking-widest uppercase font-medium">Global Monitoring Active</span>
          </div>
        </div>

        {/* Agency Directory */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-5">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-7 h-7 bg-indigo-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
              </svg>
            </div>
            <span className="text-indigo-700 font-bold text-sm">Agency Directory</span>
          </div>
          <p className="text-indigo-500 text-xs leading-relaxed mb-4">
            SceneIQ connects with over 400 jurisdictions globally. Contact our concierge for help with custom applications.
          </p>
          <button
            type="button"
            onClick={() => setConcierge(true)}
            className="w-full py-2 border border-indigo-300 rounded-lg text-indigo-600 text-sm font-semibold hover:bg-indigo-100 transition-colors"
          >
            Contact Concierge
          </button>
        </div>
      </div>

      {/* -- Main content -------------------------------------------------- */}
      <div className="flex-1 flex flex-col min-w-0 gap-4">

        {/* Header */}
        <div>
          <h1 className="text-[28px] font-bold text-slate-900 tracking-tight leading-tight">
            Jurisdiction Intelligence
          </h1>
          <p className="text-slate-500 mt-1 text-[15px]">
            Explore and filter international tax incentive profiles.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <FilterDropdown value={typeFilter}    options={ALL_TYPES}     onChange={setTypeFilter} />
          <FilterDropdown value={countryFilter} options={ALL_COUNTRIES} onChange={setCountry}    />

          <div className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, code, or country..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
            />
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            title="Refresh"
            aria-label="Refresh jurisdictions"
            className="p-2 bg-white border border-slate-200 rounded-lg text-slate-500 hover:text-slate-700 hover:border-slate-300 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Jurisdiction Map */}
        {!isLoading && jurisdictions.length > 0 && (
          <USJurisdictionMap jurisdictions={jurisdictions} onSelect={(code) => setSearch(code)} />
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
          </div>
        )}

        {/* Grid */}
        {!isLoading && filtered.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-slate-500 font-medium">No jurisdictions match your filters.</p>
              <button
                type="button"
                onClick={() => { setSearch(''); setTypeFilter('All Types'); setCountry('All Countries'); }}
                className="mt-3 text-blue-600 text-sm hover:underline"
              >
                Clear filters
              </button>
            </div>
          </div>
        )}

        {!isLoading && filtered.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 overflow-y-auto pb-2">
            {filtered.map(j => {
              const isSelected  = selectedId === j.id;
              const isSaved     = savedIds.has(j.id);
              const isAdded     = addedIds.has(j.id);
              const rate        = getBestRate(j.id);
              const minSpend    = getMinSpend(j.id);
              const creditTypes = getCreditTypes(j.id);
              const treaties    = j.treatyPartners ?? [];
              return (
                <div
                  key={j.id}
                  onClick={() => setSelectedId(j.id)}
                  className={`bg-white rounded-xl border-2 p-5 cursor-pointer flex flex-col gap-3 transition-all duration-150
                    ${isSelected
                      ? 'border-blue-500 shadow-md shadow-blue-100'
                      : 'border-slate-100 hover:border-blue-300 hover:shadow-md hover:shadow-slate-100'
                    }`}
                >
                  {/* Card header */}
                  <div className="flex items-start justify-between gap-2 min-w-0">
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-0.5">{j.code}</p>
                      <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-2">{j.name}</h3>
                    </div>
                    {rate > 0 && (
                      <span className="shrink-0 px-2 py-0.5 bg-emerald-500 text-white text-[11px] font-bold rounded-md tracking-wide">
                        {rate}%
                      </span>
                    )}
                  </div>

                  {/* Details */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 text-xs w-16 shrink-0">Country</span>
                      <span className="text-slate-700 text-xs font-semibold truncate">{j.country}</span>
                      {j.currency && j.currency !== 'USD' && (
                        <span className="ml-auto px-1.5 py-0.5 bg-slate-100 text-slate-500 text-[10px] font-bold rounded">
                          {j.currency}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 text-xs w-16 shrink-0">Min Spend</span>
                      <span className="text-slate-700 text-xs font-semibold">{minSpend}</span>
                    </div>
                    {creditTypes.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {creditTypes.map(ct => (
                          <span key={ct} className={`px-1.5 py-0.5 text-[10px] font-semibold rounded border ${CREDIT_TYPE_STYLE[ct] ?? 'bg-slate-50 text-slate-500 border-slate-200'}`}>
                            {CREDIT_TYPE_LABEL[ct] ?? ct}
                          </span>
                        ))}
                      </div>
                    )}
                    {treaties.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-slate-400 text-[10px] font-semibold uppercase tracking-wide">Treaties:</span>
                        {treaties.slice(0, 5).map(t => (
                          <span key={t} className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] font-bold rounded border border-indigo-100">
                            {t}
                          </span>
                        ))}
                        {treaties.length > 5 && (
                          <span className="text-slate-400 text-[10px]">+{treaties.length - 5} more</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Divider */}
                  <div className="border-t border-slate-100" />

                  {/* Actions */}
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={e => handleReview(j, e)}
                      className="flex items-center gap-1 text-[11px] font-bold text-slate-400 hover:text-blue-600 uppercase tracking-widest transition-colors"
                    >
                      Review
                      <ExternalLink className="w-3 h-3" />
                    </button>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={e => handleAddHint(j.name, e)}
                        className={`flex items-center gap-1 text-[11px] font-bold uppercase tracking-widest transition-colors ${
                          isAdded ? 'text-emerald-600' : 'text-blue-600 hover:text-blue-700'
                        }`}
                      >
                        {isAdded ? <><CheckCircle className="w-3 h-3" /> Added</> : 'Add to Production'}
                      </button>
                      <button
                        type="button"
                        onClick={e => toggleSave(j.id, e)}
                        title={isSaved ? 'Remove bookmark' : 'Bookmark'}
                        aria-label={isSaved ? 'Remove bookmark' : 'Bookmark'}
                        className={`transition-colors ${isSaved ? 'text-blue-600' : 'text-slate-300 hover:text-slate-500'}`}
                      >
                        <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-blue-600' : ''}`} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      {/* Concierge modal */}
      {showConcierge && <ConciergeModal onClose={() => setConcierge(false)} />}
    </div>
  );
}
