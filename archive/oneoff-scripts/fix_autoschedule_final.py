import re

# ── 1. Add autoSchedule to productionSchedule.ts ──────────────────────────
ts = open('frontend/src/api/productionSchedule.ts', 'r', encoding='utf-8').read()

new_fn = '''
// Auto-creates shoot days from unscheduled scenes based on pages per day.
export async function autoSchedule(
  productionId: string,
  pagesPerDay: number = 8,
) {
  const res = await apiClient.post(
    `/production-schedule/${productionId}/stripboard/auto-schedule`,
    null,
    { params: { pages_per_day: pagesPerDay } },
  );
  return res.data;
}
'''

if 'autoSchedule' not in ts:
    ts = ts.rstrip() + '\n' + new_fn + '\n'
    open('frontend/src/api/productionSchedule.ts', 'w', encoding='utf-8').write(ts)
    print('SUCCESS - autoSchedule added to productionSchedule.ts')
else:
    print('SKIP - autoSchedule already in productionSchedule.ts')

# ── 2. Update Stripboard.tsx ───────────────────────────────────────────────
tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# 2a. Add useState for autoScheduling and pagesPerDay after existing useState declarations
old_state = '  const [busy, setBusy] = useState(false);'
new_state = '''  const [busy, setBusy] = useState(false);
  const [autoScheduling, setAutoScheduling] = useState(false);
  const [pagesPerDay, setPagesPerDay] = useState(8);'''

if old_state in tsx and 'autoScheduling' not in tsx:
    tsx = tsx.replace(old_state, new_state, 1)
    print('State vars added')
else:
    print('SKIP - state vars already present or anchor not found')

# 2b. Add handleAutoSchedule after handleNewDay function
old_handler = '  const handleNewDay = () =>'
new_handler = '''  const handleAutoSchedule = async () => {
    if (autoScheduling) return;
    setAutoScheduling(true);
    try {
      const result = await autoSchedule(productionId, pagesPerDay) as { days_created: number; scenes_assigned: number; message: string };
      await refresh();
      alert(result.message);
    } catch {
      setError("Auto-schedule failed. Please try again.");
    } finally {
      setAutoScheduling(false);
    }
  };

  const handleNewDay = () =>'''

if old_handler in tsx and 'handleAutoSchedule' not in tsx:
    tsx = tsx.replace(old_handler, new_handler, 1)
    print('handleAutoSchedule added')
else:
    print('SKIP - handler already present or anchor not found')

# 2c. Add Auto-schedule button next to New shoot day button
old_btn = '              onClick={handleNewDay}\n              disabled={busy}'
new_btn = '''              onClick={handleNewDay}
              disabled={busy}'''

# Find the New shoot day button and add Auto-schedule after its closing tag
old_new_day_block = '''              onClick={handleNewDay}
              disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"'''

new_new_day_block = '''              onClick={handleNewDay}
              disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"'''

# Instead, find the closing of the New shoot day button and insert after
auto_btn = '''
            {unscheduled.scenes.length > 0 && (
              <div className="flex items-center gap-1.5 ml-2">
                <select
                  value={pagesPerDay}
                  onChange={e => setPagesPerDay(Number(e.target.value))}
                  className="text-xs border border-slate-200 rounded px-1.5 py-1 text-slate-600"
                >
                  <option value={4}>4 pg/day</option>
                  <option value={5}>5 pg/day</option>
                  <option value={6}>6 pg/day</option>
                  <option value={7}>7 pg/day</option>
                  <option value={8}>8 pg/day</option>
                  <option value={9}>9 pg/day</option>
                  <option value={10}>10 pg/day</option>
                </select>
                <button
                  type="button"
                  onClick={handleAutoSchedule}
                  disabled={busy || autoScheduling}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {autoScheduling ? <Loader2 size={13} className="animate-spin" /> : <LayoutGrid size={13} />}
                  Auto-schedule
                </button>
              </div>
            )}'''

# Find "New shoot day" text and insert auto button after the button's closing tag
marker = '              New shoot day\n            </button>'
if marker in tsx and 'Auto-schedule' not in tsx:
    tsx = tsx.replace(marker, marker + auto_btn, 1)
    print('Auto-schedule button added')
else:
    print('SKIP - button already present or marker not found')

open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(tsx)
print('DONE - Stripboard.tsx saved')
