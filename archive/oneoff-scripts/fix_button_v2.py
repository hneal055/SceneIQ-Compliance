tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# Find the exact button area using the context from debug output
old = '            New shoot day\n          </button>\n        </div>\n      </div>'

if old in tsx:
    new = '''            New shoot day
          </button>
          {unscheduled.scenes.length > 0 && (
            <div className="flex items-center gap-1.5 ml-2">
              <select
                value={pagesPerDay}
                onChange={(e) => setPagesPerDay(Number(e.target.value))}
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
                {autoScheduling ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <LayoutGrid size={13} />
                )}
                Auto-schedule
              </button>
            </div>
          )}
        </div>
      </div>'''
    tsx = tsx.replace(old, new, 1)
    open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(tsx)
    print('SUCCESS - button inserted')
else:
    # Try finding with different whitespace
    print('Exact match not found, searching...')
    idx = tsx.find('New shoot day')
    occurrences = []
    start = 0
    while True:
        idx = tsx.find('New shoot day', start)
        if idx == -1:
            break
        occurrences.append(idx)
        start = idx + 1
    print(f'Found {len(occurrences)} occurrences at indices: {occurrences}')
    for i in occurrences:
        snippet = tsx[i:i+100]
        print(f'\nAt {i}:', repr(snippet))
