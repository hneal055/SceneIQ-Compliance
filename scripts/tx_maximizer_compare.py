import requests

BASE = 'http://localhost:8001/api/0.1.0'
r = requests.post(f'{BASE}/auth/login', json={'email': 'admin@sceneiq.com', 'password': 'sceneiq2024'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

markets = [
    ('TX base only',    ['TX']),
    ('TX + Austin',     ['TX', 'TX-AUSTIN']),
    ('TX + Dallas',     ['TX', 'TX-DALLAS']),
    ('TX + Fort Worth', ['TX', 'TX-FORTWORTH']),
    ('TX + Houston',    ['TX', 'TX-HOUSTON']),
    ('TX + San Antonio',['TX', 'TX-SANANTONIO']),
]

print('Maximizer -- TX $5M Film Spend')
print(f"{'Market':<22} {'Grant USD':>12} {'Eff. Rate':>10}  Applied Rules")
print('-' * 90)

for label, codes in markets:
    resp = requests.post(f'{BASE}/maximize', json={
        'jurisdiction_codes': codes,
        'project_type': 'film',
        'qualified_spend': 5_000_000
    }, headers=headers)
    d = resp.json()
    incentive = d['total_incentive_usd']
    rate = d['effective_rate']
    rate_str = f"{rate*100:.1f}%" if rate else 'N/A'
    rules = ', '.join(f"{x['rule_key']} (${x['computed_value']:,.0f})" for x in d['applied_rules'])
    print(f"{label:<22} ${incentive:>11,.0f} {rate_str:>10}  {rules}")
    for w in d.get('warnings', []):
        print(f"  [opt-in] {w}")
