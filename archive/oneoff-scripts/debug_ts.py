tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# Check where handleAutoSchedule and setPagesPerDay are defined vs used
print('handleAutoSchedule defined:', 'const handleAutoSchedule' in tsx)
print('handleAutoSchedule used in JSX:', 'onClick={handleAutoSchedule}' in tsx)
print('setPagesPerDay defined:', 'setPagesPerDay' in tsx)
print('setPagesPerDay used in JSX:', 'onChange={e => setPagesPerDay' in tsx)
print('Auto-schedule in JSX:', 'Auto-schedule' in tsx)

# Find where the auto-schedule button is
idx = tsx.find('onClick={handleAutoSchedule}')
if idx != -1:
    print('\nButton found at index:', idx)
    print('Context:', repr(tsx[idx-100:idx+200]))
else:
    print('\nButton NOT found in JSX')
    
# Check if it's inside a function component or outside
idx2 = tsx.find('const handleAutoSchedule')
if idx2 != -1:
    print('\nhandleAutoSchedule defined at:', idx2)
    print('Context:', repr(tsx[idx2-50:idx2+200]))
