import urllib.request, json

with open("C:/Projects/SceneIQ-Compliance/temp_token.txt", "r") as f:
    token = f.read().strip()

base_url = "https://compliance.getsceneiq.com/api/0.1.0"
headers = {
    "Authorization": "Bearer " + token,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

markets = [
    "los_angeles", "new_york", "georgia", "new_mexico", "chicago",
    "atlanta", "new_orleans", "vancouver", "toronto", "london",
    "cape_town", "budapest", "prague", "dublin"
]

print("Testing all 14 non-union markets...\n")
all_pass = True
for market in markets:
    req = urllib.request.Request(
        f"{base_url}/rates/nonunion?location={market}",
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        rates = data.get("markets", {}).get(market) or data.get("rates")
        if rates and isinstance(rates, dict):
            role_count = len([k for k in rates if k != "notes"])
            print(f"PASS  {market} ({role_count} roles)")
        else:
            print(f"FAIL  {market} - shape: {list(data.keys())}")
            all_pass = False
    except Exception as e:
        print(f"ERROR {market}: {e}")
        all_pass = False

print()
print("Result: ALL PASS" if all_pass else "Result: SOME FAILED")
