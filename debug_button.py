tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

idx = tsx.find('Auto-schedule')
print('Auto-schedule found at:', idx)
print('Context:')
print(repr(tsx[idx-400:idx+200]))
