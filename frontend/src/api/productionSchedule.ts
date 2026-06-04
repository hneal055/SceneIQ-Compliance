// =============================================================================
// frontend/src/api/productionSchedule.ts
// Domain helpers for the Production Schedule Engine API
// (POST/GET endpoints under /api/0.1.0/production-schedule/).
//
// Pattern mirrors the per-domain function blocks in
// frontend/src/api/index.ts. No `withFallback`/mocks here — the new
// pages require the backend to be running; falling back to mock data
// would hide real integration issues.
// =============================================================================

import apiClient from "./client";

// -----------------------------------------------------------------------------
// Response shapes
// -----------------------------------------------------------------------------

export interface ImportResponse {
  scenes_imported: number;
  jurisdictions_detected: string[];
  warnings: string[];
}

export interface StripboardSceneSnapshot {
  id: string | null;
  production_id: string | null;
  scene_number: string;
  title: string | null;
  location: string | null;
  location_type: string | null;
  time_of_day: string | null;
  page_count: number | null;
  jurisdiction_id: string | null;
  cast_ids: string[];
  notes: string | null;
  shoot_day_id: string | null;
}

export interface StripboardDay {
  id: string;
  day_number: number;
  date: string | null;
  jurisdiction: string | null;
  total_pages: number;
  scenes: StripboardSceneSnapshot[];
}

export interface UnscheduledBin {
  scenes: StripboardSceneSnapshot[];
  total_pages: number;
}

// New shape: scheduled days (each with its ShootDay id) plus the
// Unscheduled bin holding every scene not yet assigned to a day.
export interface StripboardResponse {
  days: StripboardDay[];
  unscheduled: UnscheduledBin;
}

export interface AssignSceneBody {
  scene_id: string;
  shoot_day_id: string;
  position?: number | null;
}

export interface CreateShootDayBody {
  date?: string | null;
  jurisdiction_name?: string | null;
  location?: string | null;
  call_time?: string | null;
  nearest_hospital?: string | null;
  notes?: string | null;
}

// DOOD grid: outer key = cast_member.id, inner key = day_number (string in JSON),
// value = code (e.g. "SW", "W", "H", "WF", "SWF").
export type DoodGrid = Record<string, Record<string, string>>;

export interface CallSheetJson {
  id: string | null;
  production_id: string | null;
  shoot_day_id: string;
  day_number: number;
  date: string | null;
  general_call: string | null;
  location: string | null;
  nearest_hospital: string | null;
  weather: string | null;
  scenes: Array<{
    scene_number?: string;
    title?: string | null;
    location?: string | null;
    location_type?: string | null;
    time_of_day?: string | null;
    page_count?: number | null;
    cast?: string[];
  }>;
  crew_calls: Array<{
    department?: string | null;
    name?: string | null;
    call_time?: string | null;
  }>;
}

export interface JurisdictionTrackerRow {
  jurisdiction_id: string;
  jurisdiction_name: string;
  shoot_days: number;
  verified_at: string | null;
}

export type CompliancePushPayload = Record<
  string,
  { shoot_days: number; verified_at: string }
>;

// -----------------------------------------------------------------------------
// Helper functions
// -----------------------------------------------------------------------------

const BASE = "/production-schedule";

// Uploads a .csv / .mms / .fdx breakdown file and persists scenes
// against the given production.
export async function importBreakdown(
  productionId: string,
  file: File,
): Promise<ImportResponse> {
  const fd = new FormData();
  fd.append("file", file);
  // Override the default Content-Type so axios sets multipart/form-data
  // with the right boundary (same trick used by ScheduleParser/UploadPanel).
  const r = await apiClient.post<ImportResponse>(
    `${BASE}/${productionId}/import`,
    fd,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return r.data;
}

export async function getStripboard(
  productionId: string,
): Promise<StripboardResponse> {
  const r = await apiClient.get<StripboardResponse>(
    `${BASE}/${productionId}/stripboard`,
  );
  return r.data;
}

export async function assignScene(
  productionId: string,
  body: AssignSceneBody,
): Promise<unknown> {
  const r = await apiClient.post(
    `${BASE}/${productionId}/stripboard/assign`,
    body,
  );
  return r.data;
}

// Moves a scene back to the Unscheduled bin (clears its shoot day).
export async function unassignScene(
  productionId: string,
  sceneId: string,
): Promise<unknown> {
  const r = await apiClient.post(
    `${BASE}/${productionId}/stripboard/unassign`,
    { scene_id: sceneId },
  );
  return r.data;
}

// Creates a new (initially empty) shoot day; day_number is auto-assigned.
export async function createShootDay(
  productionId: string,
  body: CreateShootDayBody = {},
): Promise<unknown> {
  const r = await apiClient.post(`${BASE}/${productionId}/shoot-days`, body);
  return r.data;
}

// Deletes a shoot day; its scenes return to the Unscheduled bin.
export async function deleteShootDay(
  productionId: string,
  shootDayId: string,
): Promise<unknown> {
  const r = await apiClient.delete(
    `${BASE}/${productionId}/shoot-days/${shootDayId}`,
  );
  return r.data;
}

export async function getDood(productionId: string): Promise<DoodGrid> {
  const r = await apiClient.get<DoodGrid>(`${BASE}/${productionId}/dood`);
  return r.data;
}

// Returns the file as a Blob so the caller can trigger a download via
// URL.createObjectURL (see Calculator.tsx for the click-to-download
// pattern). Both csv and pdf flow through this single helper.
export async function downloadDood(
  productionId: string,
  format: "csv" | "pdf",
): Promise<{ blob: Blob; filename: string }> {
  const r = await apiClient.get(`${BASE}/${productionId}/dood/export`, {
    params: { format },
    responseType: "blob",
  });
  return {
    blob: r.data as Blob,
    filename: `dood_${productionId}.${format}`,
  };
}

export async function getCallSheetJson(
  productionId: string,
  dayNumber: number,
): Promise<CallSheetJson> {
  const r = await apiClient.get<CallSheetJson>(
    `${BASE}/${productionId}/call-sheet/${dayNumber}`,
  );
  return r.data;
}

export async function downloadCallSheetPdf(
  productionId: string,
  dayNumber: number,
): Promise<{ blob: Blob; filename: string }> {
  const r = await apiClient.get(
    `${BASE}/${productionId}/call-sheet/${dayNumber}/pdf`,
    { responseType: "blob" },
  );
  return {
    blob: r.data as Blob,
    filename: `call_sheet_${productionId}_day_${dayNumber}.pdf`,
  };
}

export async function getJurisdictionTracker(
  productionId: string,
): Promise<JurisdictionTrackerRow[]> {
  const r = await apiClient.get<JurisdictionTrackerRow[]>(
    `${BASE}/${productionId}/jurisdiction-tracker`,
  );
  return r.data;
}

export async function pushCompliance(
  productionId: string,
): Promise<CompliancePushPayload> {
  const r = await apiClient.post<CompliancePushPayload>(
    `${BASE}/${productionId}/compliance-bridge/push`,
  );
  return r.data;
}

// -----------------------------------------------------------------------------
// Browser download helper (Blob → file)
// Mirrors Calculator.tsx:130-144.
// -----------------------------------------------------------------------------
export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
