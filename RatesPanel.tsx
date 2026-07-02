import { useState, useEffect } from 'react';
import { Calculator, Plus, Loader2, Users } from 'lucide-react';
import api from '../api';

interface RatesPanelProps {
  productionId: string;
  onExpenseAdded: () => void;
}

const IATSE_DEPARTMENTS = [
  'camera', 'lighting', 'grip', 'art_department', 'sound', 'makeup_hair', 'costume', 'construction',
];
const SAG_TIERS = ['ultra_low', 'micro', 'low', 'modified', 'basic'];
const DGA_CATEGORIES = ['feature_film', 'tv_drama', 'tv_comedy'];
const TEAMSTERS_CATEGORIES = ['transportation', 'locations'];
const WGA_CATEGORIES = ['feature_film', 'tv_drama_one_hour'];

const GUILD_LABELS: Record<string, string> = {
  'SAG-AFTRA': 'SAG-AFTRA (Actors)',
  IATSE: 'IATSE (Crew)',
  DGA: 'DGA (Directors)',
  Teamsters: 'Teamsters (Transport/Locations)',
  WGA: 'WGA (Writers)',
};

function categoriesForGuild(guild: string): string[] {
  switch (guild) {
    case 'IATSE': return IATSE_DEPARTMENTS;
    case 'SAG-AFTRA': return SAG_TIERS;
    case 'DGA': return DGA_CATEGORIES;
    case 'Teamsters': return TEAMSTERS_CATEGORIES;
    case 'WGA': return WGA_CATEGORIES;
    default: return [];
  }
}

function labelize(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function RatesPanel({ productionId, onExpenseAdded }: RatesPanelProps) {
  const [guilds, setGuilds] = useState<string[]>([]);
  const [guild, setGuild] = useState('SAG-AFTRA');
  const [category, setCategory] = useState('basic');
  const [shootWeeks, setShootWeeks] = useState(4);
  const [results, setResults] = useState<Record<string, number | string> | null>(null);
  const [loading, setLoading] = useState(false);
  const [addingKey, setAddingKey] = useState<string | null>(null);

  useEffect(() => {
    api.rates.guilds().then((d) => setGuilds(d.guilds ?? []));
  }, []);

  useEffect(() => {
    const cats = categoriesForGuild(guild);
    if (cats.length) setCategory(cats[0]);
  }, [guild]);

  async function handleCalculate() {
    setLoading(true);
    setResults(null);
    try {
      const data = await api.rates.estimate({
        guild,
        category,
        budget_tier: guild === 'SAG-AFTRA' ? category : undefined,
        shoot_weeks: shootWeeks,
      });
      setResults(data.estimated_costs ?? {});
    } finally {
      setLoading(false);
    }
  }

  async function handleAddToBudget(role: string, amount: number) {
    setAddingKey(role);
    try {
      await api.expenses.create(productionId, {
        description: `${GUILD_LABELS[guild] ?? guild} — ${labelize(role)} (${labelize(category)})`,
        amount,
        category: guild === 'WGA' || guild === 'DGA' ? 'Above-the-Line' : 'Below-the-Line',
        isQualifying: true,
        vendorName: guild,
      } as never);
      onExpenseAdded();
    } finally {
      setAddingKey(null);
    }
  }

  const cats = categoriesForGuild(guild);
  const numericResults = results
    ? Object.entries(results).filter(
        ([k, v]) => typeof v === 'number' && k !== 'overtime_rate' && k !== 'notes'
      )
    : [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-800">Union & Crew Rate Lookup</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Guild</label>
            <select
              value={guild}
              onChange={(e) => setGuild(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-md px-3 py-2"
            >
              {(guilds.length ? guilds : Object.keys(GUILD_LABELS)).map((g) => (
                <option key={g} value={g}>{GUILD_LABELS[g] ?? g}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              {guild === 'SAG-AFTRA' ? 'Budget Tier' : 'Category'}
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-md px-3 py-2"
            >
              {cats.map((c) => (
                <option key={c} value={c}>{labelize(c)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Shoot Weeks</label>
            <input
              type="number"
              min={1}
              value={shootWeeks}
              onChange={(e) => setShootWeeks(Number(e.target.value))}
              className="w-full text-sm border border-slate-300 rounded-md px-3 py-2"
            />
          </div>
        </div>

        <button
          onClick={handleCalculate}
          disabled={loading}
          className="mt-4 inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Calculator className="w-3.5 h-3.5" />}
          Calculate Rates
        </button>
      </div>

      {results && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
            <h4 className="text-sm font-semibold text-slate-700">
              Estimated Costs &mdash; {GUILD_LABELS[guild] ?? guild} / {labelize(category)} ({shootWeeks} {shootWeeks === 1 ? 'week' : 'weeks'})
            </h4>
          </div>

          {numericResults.length === 0 ? (
            <div className="px-5 py-6 text-sm text-slate-400 text-center">
              No rate data available for this combination.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {numericResults.map(([role, amount]) => (
                <div key={role} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{labelize(role)}</div>
                    <div className="text-xs text-slate-400">${Number(amount).toLocaleString()}</div>
                  </div>
                  <button
                    onClick={() => handleAddToBudget(role, Number(amount))}
                    disabled={addingKey === role}
                    className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 rounded-md px-3 py-1.5 disabled:opacity-50"
                  >
                    {addingKey === role ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Plus className="w-3 h-3" />
                    )}
                    Add to Budget
                  </button>
                </div>
              ))}
            </div>
          )}

          {results.notes && (
            <div className="px-5 py-2.5 bg-amber-50 text-xs text-amber-700 border-t border-amber-100">
              {String(results.notes)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}