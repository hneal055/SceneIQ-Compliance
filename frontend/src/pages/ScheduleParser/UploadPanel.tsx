import { useRef, useState, type DragEvent, type ChangeEvent } from 'react';
import { Upload, Loader2, CheckCircle, AlertCircle, AlertTriangle, FileText } from 'lucide-react';
import apiClient from '../../api/client';

export interface UploadIssue {
  level: 'error' | 'warning';
  segment_index: number | null;
  field: string | null;
  message: string;
}

export interface UploadSummary {
  channel: string | null;
  date: string | null;
  source_format: 'csv' | 'xml' | 'json';
  segments_parsed: number;
  errors: UploadIssue[];
  warnings: UploadIssue[];
  events_saved: number;
}

interface Props {
  onUploaded: (summary: UploadSummary) => void;
}

const ACCEPTED = ['.csv', '.xml', '.bxf', '.json'];

function detectFormat(name: string): string {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return 'unknown';
  const ext = name.slice(dot).toLowerCase();
  if (ext === '.csv') return 'CSV';
  if (ext === '.xml' || ext === '.bxf') return 'XML / BXF';
  if (ext === '.json') return 'JSON';
  return 'unknown';
}

function isAccepted(name: string): boolean {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return false;
  return ACCEPTED.includes(name.slice(dot).toLowerCase());
}

export default function UploadPanel({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<UploadSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  function pickFile(f: File | null) {
    setSummary(null);
    setError(null);
    if (!f) { setFile(null); return; }
    if (!isAccepted(f.name)) {
      setFile(null);
      setError(`Unsupported file type. Accepted: ${ACCEPTED.join(', ')}`);
      return;
    }
    setFile(f);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    pickFile(e.dataTransfer.files?.[0] ?? null);
  }

  function onSelectChange(e: ChangeEvent<HTMLInputElement>) {
    pickFile(e.target.files?.[0] ?? null);
  }

  async function doUpload() {
    if (!file || uploading) return;
    setUploading(true);
    setSummary(null);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await apiClient.post<UploadSummary>('/schedule/upload', fd);
      setSummary(r.data);
      onUploaded(r.data);
    } catch (e: unknown) {
      let msg = 'Upload failed.';
      if (e && typeof e === 'object' && 'response' in e) {
        const resp = (e as { response?: { data?: { detail?: string } } }).response;
        if (resp?.data?.detail) msg = resp.data.detail;
      } else if (e instanceof Error) {
        msg = e.message;
      }
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  const hasErrors = summary && summary.errors.length > 0;
  const hasWarnings = summary && summary.warnings.length > 0;
  const summaryTone =
    hasErrors ? 'bg-red-50 border-red-200 text-red-900'
    : hasWarnings ? 'bg-amber-50 border-amber-200 text-amber-900'
    : summary ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
    : '';

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Upload Schedule File</h2>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'
        }`}
      >
        <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <p className="text-sm text-slate-700">
          {file ? <span className="font-medium">{file.name}</span> : 'Drop a file here, or click to browse'}
        </p>
        <p className="text-xs text-slate-500 mt-1">Accepted: {ACCEPTED.join(', ')}</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          onChange={onSelectChange}
          className="hidden"
        />
      </div>

      {file && (
        <div className="mt-4 flex items-center gap-3 text-sm text-slate-600">
          <FileText className="w-4 h-4" />
          <span><span className="font-medium">{file.name}</span> · detected format: <span className="font-medium">{detectFormat(file.name)}</span></span>
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={doUpload}
          disabled={!file || uploading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? 'Uploading...' : 'Upload & Parse'}
        </button>
        {file && !uploading && (
          <button
            type="button"
            onClick={() => pickFile(null)}
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg border bg-red-50 border-red-200 text-red-900 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {summary && (
        <div className={`mt-4 p-4 rounded-lg border ${summaryTone}`}>
          <div className="flex items-start gap-2">
            {hasErrors
              ? <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
              : hasWarnings
                ? <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0" />
                : <CheckCircle className="w-5 h-5 mt-0.5 shrink-0" />}
            <div className="flex-1 space-y-1">
              <p className="font-semibold">
                {summary.segments_parsed} segments parsed · {summary.events_saved} saved
                {' · '}{summary.errors.length} error{summary.errors.length === 1 ? '' : 's'}
                {' · '}{summary.warnings.length} warning{summary.warnings.length === 1 ? '' : 's'}
              </p>
              <p className="text-xs opacity-80">
                Channel: {summary.channel ?? '—'} · Date: {summary.date ?? '—'} · Format: {summary.source_format.toUpperCase()}
              </p>
              {(summary.errors.length > 0 || summary.warnings.length > 0) && (
                <ul className="mt-2 text-xs space-y-1">
                  {[...summary.errors, ...summary.warnings].slice(0, 10).map((issue, i) => (
                    <li key={i}>
                      <span className="font-medium uppercase">[{issue.level}]</span>{' '}
                      {issue.segment_index !== null ? `segment ${issue.segment_index} ` : ''}
                      {issue.field ? `${issue.field}: ` : ''}
                      {issue.message}
                    </li>
                  ))}
                  {summary.errors.length + summary.warnings.length > 10 && (
                    <li className="opacity-70">…and {summary.errors.length + summary.warnings.length - 10} more</li>
                  )}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
