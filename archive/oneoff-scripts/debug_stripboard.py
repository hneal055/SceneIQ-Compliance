tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# Check what's actually in the file around the New shoot day button
idx = tsx.find('New shoot day')
if idx != -1:
    print('Found "New shoot day" at index:', idx)
    print('Context:')
    print(repr(tsx[idx-200:idx+300]))
else:
    print('NOT FOUND')
