content = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# 1. Add autoSchedule function import to productionSchedule api imports
old_import = 'import {\n  assignScene,\n  createShootDay,\n  deleteShootDay,\n  getStripboard,\n  unassignScene,\n  updateShootDay,'
new_import = 'import {\n  assignScene,\n  autoSchedule,\n  createShootDay,\n  deleteShootDay,\n  getStripboard,\n  unassignScene,\n  updateShootDay,'

# 2. Add handleAutoSchedule function after handleCreateDay
old_handler = '  const handleCreateDay = useCallback(async () => {'
new_handler = '''  const [autoScheduling, setAutoScheduling] = useState(false);
  const [pagesPerDay, setPagesPerDay] = useState(8);

  const handleAutoSchedule = useCallback(async () => {
    if (unscheduled.scenes.length === 0) return;
    setAutoScheduling(true);
    try {
      const result = await autoSchedule(productionId, pagesPerDay) as { days_created: number; scenes_assigned: number; message: string };
      await refresh();
      alert(`Auto-scheduled: ${result.message}`);
    } catch {
      setError("Auto-schedule failed. Please try again.");
    } finally {
      setAutoScheduling(false);
    }
  }, [productionId, pagesPerDay, unscheduled.scenes.length, refresh]);

  const handleCreateDay = useCallback(async () => {'''

# 3. Add Auto-Schedule button next to New shoot day button
old_button = '''              <Plus size={13} />
              New shoot day
            </button>
          </div>
        </div>'''

new_button = '''              <Plus size={13} />
              New shoot day
            </button>
            {unscheduled.scenes.length > 0 && (
              <div className="flex items-center gap-1.5">
                <select
                  value={pagesPerDay}
                  onChange={e => setPagesPerDay(Number(e.target.value))}
                  className="text-xs border border-slate-200 rounded px-1.5 py-1 text-slate-600"
                  title="Pages per day"
                >
                  <option value={4}>4 pages/day</option>
                  <option value={5}>5 pages/day</option>
                  <option value={6}>6 pages/day</option>
                  <option value={7}>7 pages/day</option>
                  <option value={8}>8 pages/day</option>
                  <option value={9}>9 pages/day</option>
                  <option value={10}>10 pages/day</option>
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
            )}
          </div>
        </div>'''

# Apply changes
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print('Import updated')
else:
    print('WARNING: import not found - checking alternate format')

if old_handler in content:
    content = content.replace(old_handler, new_handler, 1)
    print('Handler added')
else:
    print('WARNING: handler insertion point not found')

if old_button in content:
    content = content.replace(old_button, new_button, 1)
    print('Button added')
else:
    print('WARNING: button insertion point not found')

open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(content)
print('DONE - Stripboard.tsx updated')
