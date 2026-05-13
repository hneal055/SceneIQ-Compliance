import { useEffect, useState, useCallback } from 'react';
import { Loader2, Trash2, Filter, X } from 'lucide-react';
import apiClient from '../../api/client';

interface ScheduleEvent {
  id: string;
  channel: string;
  scheduleDate: string | null;
  sourceFile: string;
  sourceFormat: string;
  title: string;
  episodeTitle: string | null;
  episodeNumber: string | null;
  seriesNumber: string | null;
  txTime: string | null;
  duration: string | null;
  genre: string | null;
  rightsStart: string | null;
  rightsEnd: string | null;
  assetId: string | null;
  daypart: string | null;
  importedAt: string;
  productionId: string | null;
}

interface ListResponse {
  total: number;
  page: number;
  page_size: number;
  events: ScheduleEvent[];
}

interface Props { refreshKey: number; }

const PAGE_SIZE = 50;

export default function ResultsTable({ refreshKey }: Props) {
  const [rows, setRows] = useState<ScheduleEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // filter inputs (live in inputs); applied filters (live in query) — separated so
  // typing doesn't fire a request on every keystroke.
  const [channelInput, setChannelInput] = useState('');
  const [dateInput, setDateInput] = useState('');
  const [formatInput, setFormatInput] = useState('');
  const [applied, setApplied] = useState<{ channel?: string; date?: string; source_format?: string }>({});

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await apiClient.get<ListResponse>('/schedule/events', {
        params: { ...applied, page, page_size: PAGE_SIZE },
      });
      setRows(r.data.events ?? []);
      setTotal(r.data.total ?? 0);
    } catch (e) {
      setRows([]);
      setTotal(0);
      setError(e instanceof Error ? e.message : 'Failed to load schedule events.');
    } finally {
      setLoading(false);
    }
  }, [applied, page]);

  useEffect(() => { fetchRows(); }, [fetchRows, refreshKey]);

  function applyFilters() {
    const next: { channel?: string; date?: string; source_format?: string } = {};
    if (channelInput.trim()) next.channel = channelInput.trim();
    if (dateInput.trim()) next.date = dateInput.trim();
    if (formatInput.trim()) next.source_format = formatInput.trim();
    setPage(1);
    setApplied(next);
  }

  function clearFilters() {
    setChannelInput('');
    setDateInput('');
    setFormatInput('');
    setPage(1);
    setApplied({});
  }

  async function handleDelete(id: string) {
    try {
      await apiClient.delete(`/schedule/events/${id}`);
      // optimistic refresh
      fetchRows();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed.');
    }
  }

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <header className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Saved Schedule Events</h2>
          <p className="text-xs text-slate-500">{total} total row{total === 1 ? '' : 's'}</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Filter className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Channel"
            value={channelInput}
            onChange={(e) => setChannelInput(e.target.value)}
            className="px-2 py-1.5 border border-slate-300 rounded-md text-sm w-32"
          />
          <input
            type="text"
            placeholder="Date (YYYY-MM-DD)"
            value={dateInput}
            onChange={(e) => setDateInput(e.target.value)}
            className="px-2 py-1.5 border border-slate-300 rounded-md text-sm w-44"
          />
          <select
            value={formatInput}
            onChange={(e) => setFormatInput(e.target.value)}
            className="px-2 py-1.5 border border-slate-300 rounded-md text-sm"
          >
            <option value="">Any format</option>
            <option value="csv">CSV</option>
            <option value="xml">XML</option>
            <option value="json">JSON</option>
          </select>
          <button
            type="button"
            onClick={applyFilters}
            className="px-3 py-1.5 bg-slate-900 text-white rounded-md text-sm hover:bg-slate-800"
          >
            Apply
          </button>
          {(applied.channel || applied.date || applied.source_format) && (
            <button
              type="button"
              onClick={clearFilters}
              className="px-2 py-1.5 text-slate-500 hover:text-slate-700"
              title="Clear filters"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {error && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-200 text-red-900 text-sm">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
              <th className="px-6 py-3">Channel</th>
              <th className="px-6 py-3">Date</th>
              <th className="px-6 py-3">Title</th>
              <th className="px-6 py-3">TX Time</th>
              <th className="px-6 py-3">Duration</th>
              <th className="px-6 py-3">Daypart</th>
              <th className="px-6 py-3">Format</th>
              <th className="px-6 py-3">Imported</th>
              <th className="px-6 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <tr><td colSpan={9} className="px-6 py-10 text-center text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin inline-block mr-2" /> Loading…
              </td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={9} className="px-6 py-10 text-center text-slate-400">
                No schedule events yet. Upload a file above to populate this table.
              </td></tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <td className="px-6 py-3 font-medium text-slate-900">{row.channel}</td>
                  <td className="px-6 py-3 text-slate-700">{row.scheduleDate ?? '—'}</td>
                  <td className="px-6 py-3 text-slate-900">
                    {row.title}
                    {row.episodeTitle && (
                      <span className="block text-xs text-slate-500">{row.episodeTitle}</span>
                    )}
                  </td>
                  <td className="px-6 py-3 text-slate-700 font-mono text-xs">{row.txTime ?? '—'}</td>
                  <td className="px-6 py-3 text-slate-700 font-mono text-xs">{row.duration ?? '—'}</td>
                  <td className="px-6 py-3 text-slate-700">{row.daypart ?? '—'}</td>
                  <td className="px-6 py-3">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 uppercase">
                      {row.sourceFormat}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-slate-500 text-xs">
                    {new Date(row.importedAt).toLocaleString()}
                  </td>
                  <td className="px-6 py-3">
                    <button
                      type="button"
                      onClick={() => handleDelete(row.id)}
                      title="Delete row"
                      className="text-slate-400 hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > PAGE_SIZE && (
        <footer className="px-6 py-3 border-t border-slate-200 flex items-center justify-between text-sm">
          <span className="text-slate-500">
            Page {page} of {lastPage}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
              disabled={page >= lastPage}
              className="px-3 py-1.5 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </footer>
      )}
    </section>
  );
}
