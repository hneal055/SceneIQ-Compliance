tsx = open('frontend/src/pages/ProductionSchedule/Stripboard.tsx', 'r', encoding='utf-8').read()

# Find all occurrences of New shoot day
start = 0
count = 0
while True:
    idx = tsx.find('New shoot day', start)
    if idx == -1:
        break
    count += 1
    print(f'\n=== Occurrence {count} at index {idx} ===')
    print(repr(tsx[idx-300:idx+200]))
    start = idx + 1

print(f'\nTotal occurrences: {count}')
