import { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  Zap,
  CheckCircle,
  AlertCircle,
  Loader2,
  Download,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Film,
  MapPin,
  BarChart3,
  Shield,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface MMBProject {
  projectName: string;
  genre: string;
  budget: number;
  locations: string;
  audienceScore: number;
  localHirePct: number;
  diversityScore: number;
  includeLogo: boolean;
}

interface Bonus {
  name: string;
  rate: number;
  amount: number;
}

interface Recommendation {
  jurisdiction: string;
  program_name: string;
  estimated_credit: number;
  credit_rate: number;
  qualified_spend: number;
  qualified_categories: string[];
  bonuses_applied: Bonus[];
  pre_application_checklist: string[];
  audit_readiness_score: number;
  eligible: boolean;
  ineligibility_reason: string | null;
  transferable: boolean;
}

interface EvalResult {
  project_name: string;
  genre: string;
  budget: number;
  total_estimated_credits: number;
  recommendations: Recommendation[];
  generated_at: string;
}

interface FieldErrors {
  projectName?: string;
  budget?: string;
  locations?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BACKEND_URL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`;

function fmt$(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toLocaleString()}`;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

const BLANK: MMBProject = {
  projectName: '',
  genre: 'Drama',
  budget: 0,
  locations: '',
  audienceScore: 0,
  localHirePct: 0,
  diversityScore: 0,
  includeLogo: false,
};

const GENRES = [
  'Drama', 'Comedy', 'Action', 'Thriller', 'Horror',
  'Documentary', 'Animation', 'Sci-Fi', 'Romance', 'TV Series',
];

// ─── US States & Major Cities for location extraction ─────────────────────────

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
  'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
  'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
  'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
  // Abbreviations
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
];

const MAJOR_CITIES = [
  'Los Angeles','New York','Atlanta','Chicago','Dallas','Houston','Miami',
  'Las Vegas','New Orleans','Nashville','Austin','Denver','Seattle','Portland',
  'San Francisco','Boston','Philadelphia','Phoenix','San Diego','Detroit',
  'Minneapolis','Cleveland','Pittsburgh','Baltimore','Richmond','Savannah',
  'Baton Rouge','Albuquerque','Santa Fe','Wilmington','Baton Rouge',
];

function toTitleCase(str: string): string {
  return str.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

// ─── Robust MMB CSV Parser ────────────────────────────────────────────────────

function parseMMBCsv(text: string): { budget: number; locations: string; genre: string } {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const foundLocations = new Set<string>();
  let budget = 0;
  let genre = 'Drama';

  for (const line of lines) {
    // Skip header rows
    if (/^account[,\t]/i.test(line) || /^acct[,\t]/i.test(line)) continue;

    const cols = line.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)/); // CSV-safe split
    if (cols.length < 2) continue;

    const acct = parseInt(cols[0]?.replace(/\D/g, '') || '0');
    const desc = (cols[1] ?? '').replace(/"/g, '').trim();
    const rawTotal = cols[cols.length - 1]?.replace(/[$,"]/g, '').trim();
    const total = parseFloat(rawTotal || '0') || 0;

    // ── Genre inference from account descriptions ──
    if (/documentary|docuseries|doc\b/i.test(desc)) genre = 'Documentary';
    else if (/animation|animated/i.test(desc)) genre = 'Animation';
    else if (/comedy/i.test(desc)) genre = 'Comedy';
    else if (/horror/i.test(desc)) genre = 'Horror';
    else if (/thriller/i.test(desc)) genre = 'Thriller';
    else if (/sci.?fi|science fiction/i.test(desc)) genre = 'Sci-Fi';
    else if (/tv series|television series|episodic/i.test(desc)) genre = 'TV Series';

    // ── Location extraction — multiple strategies ──

    // Strategy 1: Location account range 4100–4199 (MM Budget standard)
    if (acct >= 4100 && acct <= 4199 && desc) {
      // Extract after separator
      const sepMatch = desc.match(/[-\u2013\u2014:]\s*([A-Za-z][A-Za-z\s]{2,})/);
      if (sepMatch) {
        const candidate = toTitleCase(sepMatch[1].trim());
        if (isValidLocation(candidate)) foundLocations.add(candidate);
      }
    }

    // Strategy 2: Scan ALL description text for known US states and cities
    const allText = cols.slice(0, 4).join(' ');
    for (const state of US_STATES) {
      const regex = new RegExp(`\\b${state}\\b`, 'i');
      if (regex.test(allText)) {
        foundLocations.add(toTitleCase(state));
      }
    }
    for (const city of MAJOR_CITIES) {
      const regex = new RegExp(`\\b${city}\\b`, 'i');
      if (regex.test(allText)) {
        foundLocations.add(toTitleCase(city));
      }
    }

    // Strategy 3: "Location: X" or "Filming in X" patterns anywhere in row
    const locationPattern = desc.match(
      /(?:location[s]?\s*[:–-]\s*|filming\s+(?:in|at)\s*|shoot(?:ing)?\s+(?:in|at)\s*)([A-Za-z][A-Za-z\s,]{2,})/i
    );
    if (locationPattern) {
      const raw = locationPattern[1].trim();
      raw.split(',').forEach(part => {
        const loc = toTitleCase(part.trim());
        if (isValidLocation(loc)) foundLocations.add(loc);
      });
    }

    // ── Budget: sum line items only (skip section headers with no amount) ──
    const hasQty = cols.length >= 4 && cols[2]?.trim() !== '';
    if ((hasQty || (acct > 0 && total > 0)) && total > 0) {
      // Only add to budget if this looks like a line item not a section total
      // Heuristic: section totals usually have short or empty descriptions at round account numbers
      const isSection = acct % 100 === 0 && !hasQty;
      if (!isSection) budget += total;
    }
  }

  // Deduplicate — remove cities if their state is already present
  const locArray = [...foundLocations];
  const states = locArray.filter(l => US_STATES.some(s => s.toLowerCase() === l.toLowerCase()));
  const filtered = locArray.filter(loc => {
    // Keep states and cities not dominated by a broader state entry
    return true; // Return all — let user trim if needed
  });

  return {
    budget: Math.round(budget),
    locations: filtered.slice(0, 8).join(', '), // cap at 8 to keep field readable
    genre,
  };
}

function isValidLocation(loc: string): boolean {
  if (loc.length < 3) return false;
  if (/^(fees?|permits?|allow|scout|survey|manager|days?|weeks?|months?|unit|crew|cast|misc|total|budget|amount)$/i.test(loc)) return false;
  if (/^\d/.test(loc)) return false;
  return true;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatBadge({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl px-4 py-3 text-center ${accent ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}>
      <p className={`text-xs font-medium uppercase tracking-wide mb-1 ${accent ? 'text-indigo-200' : 'text-slate-500'}`}>{label}</p>
      <p className={`text-lg font-bold ${accent ? 'text-white' : 'text-slate-900'}`}>{value}</p>
    </div>
  );
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [open, setOpen] = useState(false);
  const eligible = rec.eligible;

  return (
    <div className={`rounded-xl border ${eligible ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-white opacity-60'}`}>
      <div className="flex items-center justify-between px-5 py-4 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-2 h-2 rounded-full shrink-0 ${eligible ? 'bg-emerald-500' : 'bg-slate-300'}`} />
          <div className="min-w-0">
            <p className="font-semibold text-sm text-slate-900 truncate">{rec.program_name}</p>
            <p className="text-xs text-slate-500 mt-0.5">{rec.jurisdiction}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0 ml-4">
          {eligible && (
            <div className="text-right">
              <p className="text-emerald-700 font-bold text-base">{fmt$(rec.estimated_credit)}</p>
              <p className="text-xs text-slate-500">{pct(rec.credit_rate)} effective</p>
            </div>
          )}
          {!eligible && rec.ineligibility_reason && (
            <p className="text-xs text-slate-400 max-w-[160px] text-right">{rec.ineligibility_reason}</p>
          )}
          {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {open && eligible && (
        <div className="border-t border-emerald-200 px-5 py-4 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-lg p-3 text-center border border-emerald-100">
              <p className="text-xs text-slate-500">Qualified Spend</p>
              <p className="font-semibold text-slate-900">{fmt$(rec.qualified_spend)}</p>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-emerald-100">
              <p className="text-xs text-slate-500">Base Rate</p>
              <p className="font-semibold text-slate-900">{pct(rec.credit_rate)}</p>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-emerald-100">
              <p className="text-xs text-slate-500">Audit Score</p>
              <p className="font-semibold text-slate-900">{rec.audit_readiness_score}/100</p>
            </div>
          </div>

          {rec.qualified_categories?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 mb-2">Eligible Categories</p>
              <div className="flex flex-wrap gap-1.5">
                {rec.qualified_categories.map(c => (
                  <span key={c} className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">{c}</span>
                ))}
              </div>
            </div>
          )}

          {rec.bonuses_applied?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 mb-2">Bonuses Applied</p>
              <div className="flex flex-wrap gap-2">
                {rec.bonuses_applied.map(b => (
                  <span key={b.name} className="px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-medium">
                    +{b.name} ({pct(b.rate)}) = {fmt$(b.amount)}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="flex justify-between items-center mb-1">
              <p className="text-xs font-semibold text-slate-600">Audit Readiness</p>
              <p className="text-xs text-slate-500">{rec.audit_readiness_score}/100</p>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-500"
                style={{ width: `${rec.audit_readiness_score}%` }}
              />
            </div>
          </div>

          {rec.pre_application_checklist?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 mb-2">Pre-Application Checklist</p>
              <ul className="space-y-1">
                {rec.pre_application_checklist.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {rec.transferable && (
            <p className="text-xs text-indigo-600 font-medium">✓ Credit is transferable</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MMBConnector() {
  const [form, setForm] = useState<MMBProject>(BLANK);
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<'manual' | 'file'>('manual');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [parseInfo, setParseInfo] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const set = (key: keyof MMBProject, value: string | number | boolean) =>
    setForm(f => ({ ...f, [key]: value }));

  async function loadDemo() {
    setLoadingDemo(true);
    setError(null);
    setFieldErrors({});
    setParseInfo(null);
    try {
      const r = await fetch(`${BACKEND_URL}/integrations/largo/demo-payload`);
      if (!r.ok) throw new Error(`Backend returned ${r.status}`);
      const data = await r.json();
      setForm({
        projectName: data.project_name || 'Peach State Chronicles',
        genre: data.genre || 'Drama',
        budget: data.budget || 950000,
        locations: (data.locations || ['Georgia', 'Atlanta', 'Savannah']).join(', '),
        audienceScore: data.audience_score || 78.5,
        localHirePct: (data.local_hire_pct || 0.20) * 100,
        diversityScore: (data.diversity_score || 0.25) * 100,
        includeLogo: data.include_logo || true,
      });
      setMode('manual');
    } catch (e: unknown) {
      setError(`Could not reach backend: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoadingDemo(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setError(null);
    setFieldErrors({});
    setParseInfo(null);
    if (!f) return;

    const projectName = toTitleCase(
      f.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
    );

    if (f.name.toLowerCase().endsWith('.csv')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const text = ev.target?.result as string;
        const parsed = parseMMBCsv(text);

        setForm(prev => ({
          ...prev,
          projectName,
          genre: parsed.genre,
          budget: parsed.budget || prev.budget,
          locations: parsed.locations || prev.locations,
        }));

        // Build a helpful info message about what was extracted
        const parts: string[] = [];
        if (parsed.budget > 0) parts.push(`budget ${fmt$(parsed.budget)}`);
        else parts.push('budget not found — please enter manually');
        if (parsed.locations) parts.push(`locations: ${parsed.locations}`);
        else parts.push('locations not detected — please enter manually');
        setParseInfo(`Parsed from CSV: ${parts.join(' · ')}`);

        // Switch to manual so user can see and verify populated fields
        setMode('manual');
      };
      reader.readAsText(f);
    } else {
      // Non-CSV: just populate project name, switch to manual for rest
      setForm(prev => ({ ...prev, projectName }));
      setParseInfo('Non-CSV file uploaded. Please fill in budget and locations manually.');
      setMode('manual');
    }
  }

  function validate(): boolean {
    const errors: FieldErrors = {};
    if (!form.projectName.trim()) errors.projectName = 'Project name is required.';
    if (!form.budget || form.budget <= 0) errors.budget = 'Enter a budget greater than $0.';
    if (!form.locations.trim()) errors.locations = 'At least one filming location is required.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function evaluate() {
    setError(null);
    if (!validate()) return;

    setLoading(true);
    setResult(null);

    const payload = {
      project_name: form.projectName,
      genre: form.genre,
      budget: Number(form.budget),
      locations: form.locations.split(',').map(l => l.trim()).filter(Boolean),
      audience_score: Number(form.audienceScore),
      include_logo: form.includeLogo,
      local_hire_pct: Number(form.localHirePct) / 100,
      diversity_score: Number(form.diversityScore) / 100,
    };

    try {
      const r = await fetch(`${BACKEND_URL}/integrations/largo/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        const detail = await r.text();
        throw new Error(detail || `HTTP ${r.status}`);
      }
      const data: EvalResult = await r.json();
      setResult(data);
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message.includes('fetch')
            ? 'Cannot reach backend. Start it with: cd backend && uvicorn app.main:app --reload --port 8002'
            : e.message
          : String(e)
      );
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setForm(BLANK);
    setFile(null);
    setResult(null);
    setError(null);
    setFieldErrors({});
    setParseInfo(null);
    if (fileRef.current) fileRef.current.value = '';
  }

  function downloadReport() {
    if (!result) return;
    const eligible = result.recommendations.filter(r => r.eligible);
    const lines = [
      `MMB CONNECTOR — INCENTIVE REPORT`,
      `Generated: ${new Date(result.generated_at).toLocaleString()}`,
      ``,
      `PROJECT: ${result.project_name}`,
      `Genre: ${result.genre}`,
      `Budget: ${fmt$(result.budget)}`,
      `Total Estimated Credits: ${fmt$(result.total_estimated_credits)}`,
      ``,
      `ELIGIBLE PROGRAMS (${eligible.length})`,
      `${'─'.repeat(50)}`,
      ...eligible.map(r => [
        `${r.jurisdiction} — ${r.program_name}`,
        `  Estimated Credit: ${fmt$(r.estimated_credit)}`,
        `  Effective Rate:   ${pct(r.credit_rate)}`,
        `  Qualified Spend:  ${fmt$(r.qualified_spend)}`,
        r.bonuses_applied.length
          ? `  Bonuses: ${r.bonuses_applied.map(b => `${b.name} +${pct(b.rate)}`).join(', ')}`
          : '',
        `  Audit Readiness: ${r.audit_readiness_score}/100`,
        ``,
      ].filter(Boolean).join('\n')),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.project_name.replace(/\s+/g, '_')}_MMB_Report.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const eligible = result?.recommendations.filter(r => r.eligible) ?? [];
  const ineligible = result?.recommendations.filter(r => !r.eligible) ?? [];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Film className="w-6 h-6 text-indigo-600" />
            MMB Connector
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Movie Magic Budgeting → SceneIQ tax incentive evaluation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadDemo}
            disabled={loadingDemo}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            {loadingDemo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            Load Demo
          </button>
          {(result || form.projectName) && (
            <button
              onClick={reset}
              className="flex items-center gap-1.5 px-3 py-2 text-sm border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-2 p-1 bg-slate-100 rounded-xl w-fit">
        {(['manual', 'file'] as const).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              mode === m ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {m === 'manual' ? 'Manual Entry' : 'Upload MMB File'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* ── LEFT: Input ── */}
        <div className="lg:col-span-2 space-y-4">

          {/* File drop zone — only shown in file mode */}
          {mode === 'file' && (
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/30 transition-colors"
            >
              <input
                ref={fileRef}
                type="file"
                title="Upload MMB file"
                accept=".mmbx,.mdb,.csv,.xlsx,.xls"
                className="hidden"
                onChange={handleFileChange}
              />
              {file ? (
                <div className="space-y-2">
                  <FileText className="w-8 h-8 text-indigo-500 mx-auto" />
                  <p className="font-semibold text-slate-800 text-sm">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                  <p className="text-xs text-indigo-600 font-medium">Click to replace</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-8 h-8 text-slate-400 mx-auto" />
                  <p className="text-sm font-medium text-slate-700">Drop or click to upload</p>
                  <p className="text-xs text-slate-400">.mmbx · .mdb · .csv · .xlsx</p>
                </div>
              )}
            </div>
          )}

          {/* CSV parse info banner */}
          {parseInfo && (
            <div className="flex items-start gap-2 px-3 py-2.5 bg-indigo-50 border border-indigo-200 rounded-lg text-xs text-indigo-700">
              <FileText className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{parseInfo}</span>
            </div>
          )}

          {/* Form fields */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Project Details</p>

            {/* Project Name */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Project Name *</label>
              <input
                value={form.projectName}
                onChange={e => { set('projectName', e.target.value); setFieldErrors(fe => ({ ...fe, projectName: undefined })); }}
                placeholder="e.g. Peach State Chronicles"
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 ${fieldErrors.projectName ? 'border-red-400 bg-red-50' : 'border-slate-200'}`}
              />
              {fieldErrors.projectName && <p className="text-xs text-red-600">{fieldErrors.projectName}</p>}
            </div>

            {/* Genre + Budget */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Genre</label>
                <select
                  value={form.genre}
                  onChange={e => set('genre', e.target.value)}
                  title="Genre"
                  aria-label="Genre"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                >
                  {GENRES.map(g => <option key={g}>{g}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Total Budget (USD) *</label>
                <input
                  type="number"
                  value={form.budget > 0 ? form.budget : ''}
                  onChange={e => { set('budget', Number(e.target.value)); setFieldErrors(fe => ({ ...fe, budget: undefined })); }}
                  placeholder="950000"
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 ${fieldErrors.budget ? 'border-red-400 bg-red-50' : 'border-slate-200'}`}
                />
                {fieldErrors.budget && <p className="text-xs text-red-600">{fieldErrors.budget}</p>}
              </div>
            </div>

            {/* Locations */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">
                <MapPin className="w-3 h-3 inline mr-1" />
                Filming Locations * <span className="text-slate-400 font-normal">(comma-separated)</span>
              </label>
              <input
                value={form.locations}
                onChange={e => { set('locations', e.target.value); setFieldErrors(fe => ({ ...fe, locations: undefined })); }}
                placeholder="Georgia, Atlanta, Savannah"
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 ${fieldErrors.locations ? 'border-red-400 bg-red-50' : 'border-slate-200'}`}
              />
              {fieldErrors.locations && <p className="text-xs text-red-600">{fieldErrors.locations}</p>}
            </div>

            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide pt-1">Bonus Factors</p>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Audience Score (0–100)</label>
                <input
                  type="number" min="0" max="100"
                  value={form.audienceScore || ''}
                  onChange={e => set('audienceScore', Number(e.target.value))}
                  placeholder="78.5"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Local Hire % (0–100)</label>
                <input
                  type="number" min="0" max="100"
                  value={form.localHirePct || ''}
                  onChange={e => set('localHirePct', Number(e.target.value))}
                  placeholder="20"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Diversity Score (0–100)</label>
                <input
                  type="number" min="0" max="100"
                  value={form.diversityScore || ''}
                  onChange={e => set('diversityScore', Number(e.target.value))}
                  placeholder="25"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <div
                    onClick={() => set('includeLogo', !form.includeLogo)}
                    className={`w-9 h-5 rounded-full transition-colors ${form.includeLogo ? 'bg-indigo-600' : 'bg-slate-300'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full shadow mt-0.5 transition-transform ${form.includeLogo ? 'translate-x-4' : 'translate-x-0.5'}`} />
                  </div>
                  <span className="text-xs font-medium text-slate-600">Promo Logo (+10%)</span>
                </label>
              </div>
            </div>

            <button
              onClick={evaluate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60 transition-colors mt-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {loading ? 'Evaluating…' : 'Send to SceneIQ'}
            </button>
          </div>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="lg:col-span-3 space-y-4">

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && !error && (
            <div className="flex flex-col items-center justify-center py-20 text-center space-y-3 bg-white border border-slate-200 rounded-xl">
              <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center">
                <BarChart3 className="w-7 h-7 text-indigo-500" />
              </div>
              <p className="font-semibold text-slate-700">No results yet</p>
              <p className="text-sm text-slate-400 max-w-xs">
                Fill in project details and click <strong>Send to SceneIQ</strong>, or load the demo to try it instantly.
              </p>
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 animate-pulse">
              <div className="h-4 bg-slate-200 rounded w-1/2" />
              <div className="h-12 bg-indigo-100 rounded-xl" />
              <div className="h-20 bg-slate-100 rounded-xl" />
              <div className="h-20 bg-slate-100 rounded-xl" />
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wide font-medium">Project</p>
                    <p className="font-bold text-slate-900 text-lg">{result.project_name}</p>
                    <p className="text-xs text-slate-500">{result.genre} · {fmt$(result.budget)}</p>
                  </div>
                  <button
                    onClick={downloadReport}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Report
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <StatBadge label="Total Credits" value={fmt$(result.total_estimated_credits)} accent />
                  <StatBadge label="Eligible Programs" value={String(eligible.length)} />
                  <StatBadge label="Ineligible" value={String(ineligible.length)} />
                </div>

                {result.budget > 0 && (
                  <div>
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>Credits vs. Budget</span>
                      <span>{((result.total_estimated_credits / result.budget) * 100).toFixed(1)}% return</span>
                    </div>
                    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-700"
                        style={{ width: `${Math.min((result.total_estimated_credits / result.budget) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {eligible.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <p className="text-sm font-semibold text-slate-700">Eligible Programs</p>
                  </div>
                  {eligible.map((rec, i) => <RecommendationCard key={i} rec={rec} />)}
                </div>
              )}

              {ineligible.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-slate-400" />
                    <p className="text-sm font-semibold text-slate-500">Not Eligible</p>
                  </div>
                  {ineligible.map((rec, i) => <RecommendationCard key={i} rec={rec} />)}
                </div>
              )}

              <p className="text-xs text-slate-400 text-right pt-1">
                Generated {new Date(result.generated_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Info footer */}
      <div className="grid grid-cols-3 gap-4 pt-2">
        {[
          { icon: Film, label: 'Formats Supported', text: '.mmbx · .mdb · .csv · .xlsx' },
          { icon: DollarSign, label: 'Incentive Engine', text: 'Largo + SceneIQ integration' },
          { icon: MapPin, label: 'Jurisdictions', text: '23 US, Canadian & International' },
        ].map(({ icon: Icon, label, text }) => (
          <div key={label} className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
            <Icon className="w-5 h-5 text-indigo-500 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-slate-700">{label}</p>
              <p className="text-xs text-slate-500">{text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
