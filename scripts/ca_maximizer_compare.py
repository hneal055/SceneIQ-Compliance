import requests

BASE = 'http://localhost:8001/api/0.1.0'
r = requests.post(f'{BASE}/auth/login', json={'email': 'admin@sceneiq.com', 'password': 'sceneiq2024'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

markets = [
    ('Los Angeles',   ['CA', 'CA-LA']),
    ('San Francisco', ['CA', 'CA-SANFRANCISCO']),
    ('San Diego',     ['CA', 'CA-SANDIEGO']),
    ('Sacramento',    ['CA', 'CA-SACRAMENTO']),
    ('Oakland',       ['CA', 'CA-OAKLAND']),
]

print('Maximizer — $5M Film Spend across CA Markets')
print(f"{'Market':<16} {'Incentive USD':>14} {'Eff. Rate':>10} {'Rules':>6}  Applied Rules")
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
    rate_str = f"{rate*100:.4f}%" if rate else 'N/A'
    applied = d['applied_rules']
    rule_summary = ', '.join(
        f"{x['rule_key']} (${x['computed_value']:,.0f})" for x in applied
    )
    print(f"{label:<16} ${incentive:>13,.0f} {rate_str:>10} {len(applied):>6}  {rule_summary}")
