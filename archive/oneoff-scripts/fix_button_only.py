tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

if 'Auto-schedule' in tsx:
    print('SKIP - Auto-schedule button already present')
else:
    old = '              <Plus size={13} />\n              New shoot day\n            </button>'
    new = '''              <Plus size={13} />
              New shoot day
            </button>
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

    if old in tsx:
        tsx = tsx.replace(old, new, 1)
        open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(tsx)
        print('SUCCESS - Auto-schedule button added')
    else:
        print('NOT FOUND - trying alternate search')
        # Find position manually
        idx = tsx.find('New shoot day\n            </button>')
        if idx != -1:
            insert_at = idx + len('New shoot day\n            </button>')
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
            tsx = tsx[:insert_at] + auto_btn + tsx[insert_at:]
            open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(tsx)
            print('SUCCESS - Auto-schedule button added via index method')
        else:
            print('FAILED - could not find insertion point')
