tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

old = '      await refresh();'
new = '      await load();'

if old in tsx:
    tsx = tsx.replace(old, new, 1)
    open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'w', encoding='utf-8').write(tsx)
    print('SUCCESS - refresh replaced with load')
else:
    print('NOT FOUND')
