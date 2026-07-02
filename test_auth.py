import urllib.request, json

with open("C:/Projects/SceneIQ-Compliance/temp_token.txt", "r") as f:
    token = f.read().strip()

base_url = "https://compliance.getsceneiq.com/api/0.1.0"

req = urllib.request.Request(
    f"{base_url}/rates/guilds",
    headers={
        "Authorization": "Bearer " + token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print("OK:", data)
except Exception as e:
    print("ERR:", e)
