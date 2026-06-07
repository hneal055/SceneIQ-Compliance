import apiClient from './client';
import type {
  Production,
  Jurisdiction,
  IncentiveRule,
  Expense,
  CalculationResult,
  HealthStatus,
  MonitoringEvent,
  MonitoringSource,
  ComplianceItem,
  ComplianceStats,
  NotificationPreference,
  UserProfile,
  PendingRule,
  LocalRule,
  MaximizeResult,
  ChecklistResponse,
  UserScenario,
  MaximumPossibleCreditResponse,
  DetectedConflict,
} from '../types';

import { mockApi } from '../mocks/api';

// Wraps every API call with flag check + automatic mock fallback on failure.
// Reads from getFlagSnapshot() so runtime flag toggles (via FeatureFlagContext) take effect
// immediately on the next call — no page reload needed.
// READ operations fall back to mock data silently (good for dev with backend down).
// WRITE operations re-throw after logging so callers can handle the error.
async function withFallback<T>(
  realFn: () => Promise<T>,
  mockFn: () => Promise<T>,
  label: string,
  isRead = true,
): Promise<T> {
  if (false) {
    if (import.meta.env.DEV) console.log(`[MOCK] ${label}`);
    return mockFn();
  }
  try {
    if (import.meta.env.DEV) console.log(`[API] ${label}`);
    return await realFn();
  } catch (error) {
    if (isRead) {
      if (import.meta.env.DEV) console.warn(`[FALLBACK] ${label} — API unavailable, using mock data`, error);
      return mockFn();
    }
    console.error(`[API ERROR] ${label}`, error);
    throw error;
  }
}

export const api = {
  health: () =>
    withFallback(
      async () => { const r = await apiClient.get('/health'); return r.data as HealthStatus; },
      () => mockApi.health(),
      'health',
    ),

  productions: {
    list: () =>
      withFallback(
        async () => { const r = await apiClient.get('/productions'); return (r.data.productions ?? r.data) as Production[]; },
        () => mockApi.productions.list(),
        'productions.list',
      ),

    get: (id: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/productions/${id}`); return r.data as Production; },
        () => mockApi.productions.get(id),
        `productions.get(${id})`,
      ),

    create: (data: Partial<Production>) =>
      withFallback(
        async () => { const r = await apiClient.post('/productions', data); return r.data as Production; },
        () => mockApi.productions.create(data),
        'productions.create',
        false,
      ),

    update: (id: string, data: Partial<Production>) =>
      withFallback(
        async () => { const r = await apiClient.put(`/productions/${id}`, data); return r.data as Production; },
        () => mockApi.productions.update(id, data),
        `productions.update(${id})`,
        false,
      ),

    delete: (id: string) =>
      withFallback(
        async () => { await apiClient.delete(`/productions/${id}`); },
        () => mockApi.productions.delete(id),
        `productions.delete(${id})`,
        false,
      ),
  },

  jurisdictions: {
    list: () =>
      withFallback(
        async () => { const r = await apiClient.get('/jurisdictions'); return (r.data.jurisdictions ?? r.data) as Jurisdiction[]; },
        () => mockApi.jurisdictions.list(),
        'jurisdictions.list',
      ),

    get: (id: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/jurisdictions/${id}`); return r.data as Jurisdiction; },
        () => mockApi.jurisdictions.get(id),
        `jurisdictions.get(${id})`,
      ),
  },

  incentiveRules: {
    list: () =>
      withFallback(
        async () => { const r = await apiClient.get('/incentive-rules'); return (r.data.rules ?? r.data) as IncentiveRule[]; },
        () => mockApi.incentiveRules.list(),
        'incentiveRules.list',
      ),

    getByJurisdiction: (jurisdictionId: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/incentive-rules?jurisdiction_id=${jurisdictionId}`); return (r.data.rules ?? r.data) as IncentiveRule[]; },
        () => mockApi.incentiveRules.getByJurisdiction(jurisdictionId),
        `incentiveRules.getByJurisdiction(${jurisdictionId})`,
      ),
  },

  expenses: {
    list: (productionId: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/productions/${productionId}/expenses`); return (r.data.expenses ?? r.data) as Expense[]; },
        () => mockApi.expenses.list(productionId),
        `expenses.list(${productionId})`,
      ),

    create: (productionId: string, data: Partial<Expense> & { expenseDate?: string; isQualifying?: boolean; description?: string; vendorName?: string }) =>
      withFallback(
        async () => { const r = await apiClient.post(`/productions/${productionId}/expenses`, data); return r.data as Expense; },
        () => mockApi.expenses.create(productionId, data),
        `expenses.create(${productionId})`,
        false,
      ),

    delete: (productionId: string, expenseId: string) =>
      withFallback(
        async () => { await apiClient.delete(`/productions/${productionId}/expenses/${expenseId}`); },
        () => mockApi.expenses.delete(productionId, expenseId),
        `expenses.delete(${productionId}/${expenseId})`,
        false,
      ),

    generate: (productionId: string, replace = false) =>
      withFallback(
        async () => {
          const r = await apiClient.post(
            `/productions/${productionId}/expenses/generate?replace=${replace}`
          );
          return r.data as { created: number; totalAmount: number; qualifyingAmount: number; expenses: Expense[] };
        },
        async () => ({ created: 0, totalAmount: 0, qualifyingAmount: 0, expenses: [] as Expense[] }),
        `expenses.generate(${productionId})`,
        false,
      ),
  },

  calculations: {
    calculate: (productionId: string, jurisdictionId: string) =>
      withFallback(
        async () => {
          const r = await apiClient.post('/calculate', { production_id: productionId, jurisdiction_id: jurisdictionId });
          return r.data as CalculationResult;
        },
        () => mockApi.calculations.calculate(productionId, jurisdictionId),
        `calculations.calculate(${productionId}, ${jurisdictionId})`,
      ),
  },

  compliance: {
    list: (productionId: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/productions/${productionId}/compliance`); return r.data as ComplianceStats; },
        async () => ({ total: 0, complete: 0, pending: 0, waived: 0, pct: 0, items: [] as ComplianceItem[] }),
        `compliance.list(${productionId})`,
      ),

    generate: (productionId: string) =>
      withFallback(
        async () => { const r = await apiClient.post(`/productions/${productionId}/compliance/generate`); return r.data as { created: number; items: ComplianceItem[] }; },
        async () => ({ created: 0, items: [] as ComplianceItem[] }),
        `compliance.generate(${productionId})`,
        false,
      ),

    addItem: (productionId: string, data: { label: string; category?: string; notes?: string }) =>
      withFallback(
        async () => { const r = await apiClient.post(`/productions/${productionId}/compliance`, data); return r.data as ComplianceItem; },
        async () => ({} as ComplianceItem),
        `compliance.addItem(${productionId})`,
        false,
      ),

    updateItem: (itemId: string, data: { status?: string; notes?: string; label?: string }) =>
      withFallback(
        async () => { const r = await apiClient.patch(`/compliance/${itemId}`, data); return r.data as ComplianceItem; },
        async () => ({} as ComplianceItem),
        `compliance.updateItem(${itemId})`,
        false,
      ),

    deleteItem: (itemId: string) =>
      withFallback(
        async () => { await apiClient.delete(`/compliance/${itemId}`); },
        async () => {},
        `compliance.deleteItem(${itemId})`,
        false,
      ),
  },

  notifications: {
    getPreferences: () =>
      withFallback(
        async () => { const r = await apiClient.get('/notifications/preferences'); return r.data as NotificationPreference | null; },
        async () => null,
        'notifications.getPreferences',
      ),

    upsertPreferences: (data: { emailAddress: string; jurisdictions: string[]; active: boolean; reportFrequency?: string }) =>
      withFallback(
        async () => { const r = await apiClient.post('/notifications/preferences', data); return r.data as NotificationPreference; },
        async () => ({} as NotificationPreference),
        'notifications.upsertPreferences',
        false,
      ),

    deletePreferences: () =>
      withFallback(
        async () => { await apiClient.delete('/notifications/preferences'); },
        async () => {},
        'notifications.deletePreferences',
        false,
      ),
  },

  admin: {
    listUsers: () =>
      withFallback(
        async () => { const r = await apiClient.get('/admin/users'); return r.data as { total: number; users: UserProfile[] }; },
        async () => ({ total: 0, users: [] as UserProfile[] }),
        'admin.listUsers',
      ),

    createUser: (data: { email: string; password: string; role: string }) =>
      withFallback(
        async () => { const r = await apiClient.post('/admin/users', data); return r.data as UserProfile; },
        async () => ({} as UserProfile),
        'admin.createUser',
        false,
      ),

    updateUser: (userId: string, data: { role?: string; isActive?: boolean; password?: string }) =>
      withFallback(
        async () => { const r = await apiClient.patch(`/admin/users/${userId}`, data); return r.data as UserProfile; },
        async () => ({} as UserProfile),
        `admin.updateUser(${userId})`,
        false,
      ),

    deleteUser: (userId: string) =>
      withFallback(
        async () => { await apiClient.delete(`/admin/users/${userId}`); },
        async () => {},
        `admin.deleteUser(${userId})`,
        false,
      ),
  },

  maximizer: {
    maximize: (params: {
      lat?: number;
      lng?: number;
      jurisdiction_codes?: string[];
      project_type?: string;
      qualified_spend?: number;
      spend_by_location?: Record<string, number>;
    }) =>
      withFallback(
        async () => {
          const r = await apiClient.post('/maximize', params);
          return r.data as MaximizeResult;
        },
        async () => ({
          resolved_state: null,
          jurisdictions_evaluated: 0,
          qualified_spend: params.qualified_spend ?? null,
          total_incentive_usd: 0,
          effective_rate: null,
          breakdown: {},
          applied_rules: [],
          overridden_rules: [],
          warnings: ['API unavailable — showing empty result'],
          recommendations: [],
        } as MaximizeResult),
        'maximizer.maximize',
        false,
      ),

    lookup: (lat: number, lng: number) =>
      withFallback(
        async () => {
          const r = await apiClient.get('/maximize/lookup', { params: { lat, lng } });
          return r.data as { resolved_state: string | null; jurisdictions: { id: string; name: string; code: string; type: string }[] };
        },
        async () => ({ resolved_state: null, jurisdictions: [] }),
        'maximizer.lookup',
      ),

    getMaximumPossibleCredit: (params?: { jurisdiction?: string; budget?: number }) =>
      withFallback(
        async () => {
          const r = await apiClient.get('/maximize/maximum-possible-credit', { params });
          return r.data as MaximumPossibleCreditResponse;
        },
        async () => ({ summaries: [], best_case_headline: null, generated_at: new Date().toISOString() } as MaximumPossibleCreditResponse),
        'maximizer.getMaximumPossibleCredit',
      ),
  },

  georgia: {
    getJurisdiction: (code: string) =>
      withFallback(
        async () => { const r = await apiClient.get(`/georgia/jurisdictions/${code}`); return r.data as { id: string; code: string; name: string; country: string; type: string; description: string | null; website: string | null; active: boolean }; },
        async () => ({ id: '', code, name: 'Georgia', country: 'USA', type: 'state', description: null, website: null, active: true }),
        `georgia.getJurisdiction(${code})`,
      ),

    getPrograms: (code: string) =>
      withFallback(
        async () => {
          const r = await apiClient.get(`/georgia/jurisdictions/${code}/programs`);
          return r.data as {
            jurisdiction_id: string;
            jurisdiction_name: string;
            jurisdiction_code: string;
            currency: string;
            treaty_partners: string[];
            total: number;
            programs: Array<{
              id: string;
              name: string;
              code: string;
              incentive_type: string;
              credit_type: string | null | undefined;
              percentage: number;
              min_spend: number | null;
              max_credit: number | null;
              eligible_expenses: string[] | null;
              excluded_expenses: string[] | null;
              requirements: string | string[] | null;
              effective_date: string | null;
              active: boolean;
            }>;
          };
        },
        async () => ({ jurisdiction_id: '', jurisdiction_name: 'Georgia', jurisdiction_code: code, currency: 'USD', treaty_partners: [], total: 0, programs: [] }),
        `georgia.getPrograms(${code})`,
      ),
  },

  advisor: {
    summarizeEvent: (eventId: string) =>
      withFallback(
        async () => {
          const r = await apiClient.post(`/advisor/summarize-event/${eventId}`);
          return r.data as MonitoringEvent;
        },
        async () => ({} as MonitoringEvent),
        `advisor.summarizeEvent(${eventId})`,
        false,
      ),
  },

  monitoring: {
    events: {
      list: (params?: { limit?: number; skip?: number; unread_only?: boolean }) =>
        withFallback(
          async () => {
            const r = await apiClient.get('/monitoring/events', { params });
            return r.data as { total: number; unread: number; events: MonitoringEvent[] };
          },
          async () => ({ total: 0, unread: 0, events: [] as MonitoringEvent[] }),
          'monitoring.events.list',
        ),

      unreadCount: () =>
        withFallback(
          async () => { const r = await apiClient.get('/monitoring/events/unread-count'); return r.data as { count: number }; },
          async () => ({ count: 0 }),
          'monitoring.events.unreadCount',
        ),

      markRead: (id: string) =>
        withFallback(
          async () => { const r = await apiClient.patch(`/monitoring/events/${id}/read`); return r.data as MonitoringEvent; },
          async () => ({} as MonitoringEvent),
          `monitoring.events.markRead(${id})`,
          false,
        ),

      markAllRead: () =>
        withFallback(
          async () => { const r = await apiClient.post('/monitoring/events/mark-all-read'); return r.data as { updated: number }; },
          async () => ({ updated: 0 }),
          'monitoring.events.markAllRead',
          false,
        ),
    },

    sources: {
      list: () =>
        withFallback(
          async () => { const r = await apiClient.get('/monitoring/sources'); return r.data as { total: number; sources: MonitoringSource[] }; },
          async () => ({ total: 0, sources: [] as MonitoringSource[] }),
          'monitoring.sources.list',
        ),

      create: (data: Partial<MonitoringSource>) =>
        withFallback(
          async () => { const r = await apiClient.post('/monitoring/sources', data); return r.data as MonitoringSource; },
          async () => ({} as MonitoringSource),
          'monitoring.sources.create',
          false,
        ),
    },
  },

  requirements: {
    getChecklist: (code: string, projectType?: string) =>
      withFallback(
        async () => {
          const r = await apiClient.get(`/jurisdictions/${code}/requirements`, {
            params: { project_type: projectType, include_parent: true },
          });
          return r.data as ChecklistResponse;
        },
        async () => ({
          jurisdictionCode: code,
          jurisdictionName: code,
          projectType: projectType ?? null,
          total: 0,
          byCategory: {},
          requirements: [],
        } as ChecklistResponse),
        `requirements.getChecklist(${code})`,
      ),
  },

  scenarios: {
    list: () =>
      withFallback(
        async () => { const r = await apiClient.get('/scenarios'); return r.data as UserScenario[]; },
        async () => [] as UserScenario[],
        'scenarios.list',
      ),

    create: (data: { name: string; codes: string; spend: string; projectType: string; splitSpend: Record<string, string> }) =>
      withFallback(
        async () => { const r = await apiClient.post('/scenarios', data); return r.data as UserScenario; },
        async () => ({} as UserScenario),
        'scenarios.create',
        false,
      ),

    delete: (id: string) =>
      withFallback(
        async () => { await apiClient.delete(`/scenarios/${id}`); },
        async () => {},
        `scenarios.delete(${id})`,
        false,
      ),
  },
};

export const localRulesApi = {
  list: async (params?: { jurisdictionId?: string; jurisdictionCode?: string; category?: string; activeOnly?: boolean }): Promise<{ total: number; rules: LocalRule[] }> => {
    const r = await apiClient.get('/local-rules', { params: { active_only: params?.activeOnly ?? true, ...params } });
    return r.data;
  },
  byJurisdiction: async (code: string): Promise<{ jurisdiction: { id: string; name: string; code: string; type: string; parentId: string | null }; total: number; rules: LocalRule[] }> => {
    const r = await apiClient.get(`/local-rules/by-jurisdiction/${code}`);
    return r.data;
  },
  get: async (id: string): Promise<LocalRule> => {
    const r = await apiClient.get(`/local-rules/${id}`);
    return r.data;
  },
  deactivate: async (id: string): Promise<void> => {
    await apiClient.delete(`/local-rules/${id}`);
  },
  stats: async (): Promise<{ total: number; active: number; bySource: { extractedBy: string; count: number }[]; byCategory: { category: string; count: number }[] }> => {
    const r = await apiClient.get('/local-rules/stats/summary');
    return r.data;
  },
};

export const pendingRulesApi = {
  list: async (status?: string): Promise<{ total: number; pendingCount: number; rules: PendingRule[] }> => {
    const params = status ? { status } : {};
    const r = await apiClient.get('/pending-rules', { params });
    return r.data;
  },
  get: async (id: string): Promise<PendingRule> => {
    const r = await apiClient.get(`/pending-rules/${id}`);
    return r.data;
  },
  approve: async (id: string, reviewNotes?: string): Promise<PendingRule & { promotedRules: number }> => {
    const r = await apiClient.patch(`/pending-rules/${id}/approve`, { reviewNotes });
    return r.data;
  },
  reject: async (id: string, reviewNotes?: string): Promise<PendingRule> => {
    const r = await apiClient.patch(`/pending-rules/${id}/reject`, { reviewNotes });
    return r.data;
  },
};

export const getApiUrl = (path: string): string => {
  const base = import.meta.env.VITE_API_URL ?? '';
  return base + path;
};

// Conflict engine (ported from incentives-app). Routes live under
// /api/0.1.0/conflicts (apiClient prepends the versioned base).
export const conflictsApi = {
  list: async (params?: {
    project_id?: string;
    conflict_type?: string;
    unresolved_only?: boolean;
    limit?: number;
    skip?: number;
  }): Promise<{ total: number; conflicts: DetectedConflict[] }> => {
    const r = await apiClient.get('/conflicts', { params });
    return r.data;
  },

  get: async (id: string): Promise<DetectedConflict> => {
    const r = await apiClient.get(`/conflicts/${id}`);
    return r.data;
  },

  resolve: async (
    id: string,
    body: { strategy_name: string; resolved_by?: string; notes?: string }
  ): Promise<DetectedConflict> => {
    const r = await apiClient.post(`/conflicts/${id}/resolve`, body);
    return r.data;
  },

  override: async (
    id: string,
    body: { chosen_rule_key: string; chosen_value?: number | null; chosen_by?: string; notes?: string }
  ): Promise<{ override: object; conflict_id: string }> => {
    const r = await apiClient.post(`/conflicts/${id}/override`, body);
    return r.data;
  },
};

export default api;
