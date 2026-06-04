// =============================================================================
// frontend/src/pages/ProductionSchedule/ImportPanel.tsx
// Drag-and-drop upload for .csv / .mms / .fdx script breakdowns.
// Posts to POST /production-schedule/{productionId}/import and renders a
// green/amber/red result panel plus an "imported scenes" preview table
// that re-fetches /stripboard so the user can see what landed in the DB.
//
// Upload pattern mirrors ScheduleParser/UploadPanel.tsx:101-174.
// =============================================================================

import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  FileText,
  Loader2,
  Upload,
} from "lucide-react";

import {
  getStripboard,
  importBreakdown,
  type ImportResponse,
  type StripboardSceneSnapshot,
} from "../../api/productionSchedule";

interface Props {
  productionId: string;
}

const ACCEPTED = [".csv", ".mms", ".fdx"];

function isAccepted(name: string): boolean {
  const dot = name.lastIndexOf(".");
  if (dot < 0) return false;
  return ACCEPTED.includes(name.slice(dot).toLowerCase());
}

function detectFormat(name: string): string {
  const dot = name.lastIndexOf(".");
  if (dot < 0) return "unknown";
  const ext = name.slice(dot).toLowerCase();
  if (ext === ".csv") return "CSV";
  if (ext === ".mms") return "Movie Magic Scheduling";
  if (ext === ".fdx") return "Final Draft";
  return "unknown";
}

// FastAPI returns errors as either {detail: "string"} or {detail: [...]}.
// Same coercer used in ScheduleParser/UploadPanel.tsx.
function extractErrorMessage(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: unknown } } }).response;
    const detail = resp?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          if (d && typeof d === "object" && "msg" in d) {
            return String((d as { msg: unknown }).msg);
          }
          return JSON.stringify(d);
        })
        .join("; ");
    }
    if (detail) return JSON.stringify(detail);
  }
  if (e instanceof Error) return e.message;
  return "Upload failed.";
}

export default function ImportPanel({ productionId }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<StripboardSceneSnapshot[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Reset the result panel whenever the selected production changes.
  useEffect(() => {
    setSummary(null);
    setError(null);
    setPreview([]);
  }, [productionId]);

  function pickFile(f: File | null) {
    setSummary(null);
    setError(null);
    if (!f) {
      setFile(null);
      return;
    }
    if (!isAccepted(f.name)) {
      setFile(null);
      setError(`Unsupported file type. Accepted: ${ACCEPTED.join(", ")}`);
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
    if (!file || uploading || !productionId) return;
    setUploading(true);
    setSummary(null);
    setError(null);
    setPreview([]);
    try {
      const r = await importBreakdown(productionId, file);
      setSummary(r);

      // After a successful upload, pull the stripboard so the user can see
      // the persisted scenes — the import endpoint only returns counts.
      setPreviewLoading(true);
      try {
        const sb = await getStripboard(productionId);
        // Freshly-imported scenes land in the Unscheduled bin (no shoot day
        // yet); include those first, then any already on shoot days, so the
        // preview confirms exactly what just landed in the DB.
        const flattened: StripboardSceneSnapshot[] = [
          ...sb.unscheduled.scenes,
          ...sb.days.flatMap((day) => day.scenes),
        ];
        setPreview(flattened.slice(0, 10));
      } catch {
        // Preview is informational — don't surface stripboard fetch errors
        // through the import flow.
      } finally {
        setPreviewLoading(false);
      }
    } catch (e: unknown) {
      setError(extractErrorMessage(e));
    } finally {
      setUploading(false);
    }
  }

  const hasWarnings = summary && summary.warnings.length > 0;
  const tone = hasWarnings
    ? "bg-amber-50 border-amber-200 text-amber-900"
    : summary
      ? "bg-emerald-50 border-emerald-200 text-emerald-900"
      : "";

  return (
    <section className="space-y-6">
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Upload script breakdown
        </h2>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 bg-slate-50 hover:bg-slate-100"
          }`}
        >
          <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <p className="text-sm text-slate-700">
            {file ? (
              <span className="font-medium">{file.name}</span>
            ) : (
              "Drop a file here, or click to browse"
            )}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Accepted: {ACCEPTED.join(", ")}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(",")}
            onChange={onSelectChange}
            className="hidden"
          />
        </div>

        {file && (
          <div className="mt-4 flex items-center gap-3 text-sm text-slate-600">
            <FileText className="w-4 h-4" />
            <span>
              <span className="font-medium">{file.name}</span> · detected
              format: <span className="font-medium">{detectFormat(file.name)}</span>
            </span>
          </div>
        )}

        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            onClick={doUpload}
            disabled={!file || uploading || !productionId}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {uploading ? "Uploading…" : "Upload & Parse"}
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
          <div className={`mt-4 p-4 rounded-lg border ${tone}`}>
            <div className="flex items-start gap-2">
              {hasWarnings ? (
                <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0" />
              ) : (
                <CheckCircle className="w-5 h-5 mt-0.5 shrink-0" />
              )}
              <div className="flex-1">
                <p className="font-semibold text-sm">
                  Imported {summary.scenes_imported}{" "}
                  {summary.scenes_imported === 1 ? "scene" : "scenes"}
                  {hasWarnings ? " — with warnings" : ""}
                </p>

                {summary.jurisdictions_detected.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-xs font-medium opacity-80">
                      Jurisdictions seen:
                    </span>
                    {summary.jurisdictions_detected.map((name) => (
                      <span
                        key={name}
                        className="text-[11px] px-2 py-0.5 rounded-full bg-white/60 border border-current/20"
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                )}

                {summary.warnings.length > 0 && (
                  <ul className="mt-2 text-xs space-y-1 list-disc list-inside opacity-90">
                    {summary.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Imported-scenes preview table (first 10 scenes from the stripboard) */}
      {(previewLoading || preview.length > 0) && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-900">
              Imported scenes preview
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              First 10 scenes pinned to a shoot day. Visit the Stripboard tab
              for the full grid.
            </p>
          </div>
          {previewLoading ? (
            <div className="px-6 py-8 text-center text-sm text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin inline-block mr-2" />
              Loading scenes…
            </div>
          ) : (
            <table className="min-w-full">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Scene #
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Int/Ext
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Day/Night
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Pages
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {preview.map((s, i) => (
                  <tr key={s.id ?? i} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-slate-900">
                      {s.scene_number}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {s.title ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {s.location ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {s.location_type ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {s.time_of_day ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-700">
                      {s.page_count ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
}
