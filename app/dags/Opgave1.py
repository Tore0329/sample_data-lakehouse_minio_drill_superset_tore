import json
import requests

res = requests.get('https://sa-mp.im/api/v1/players/get')
resjson = res.json()
print(f"Count: {len(resjson)} ->\n{json.dumps(resjson, indent=4)}")