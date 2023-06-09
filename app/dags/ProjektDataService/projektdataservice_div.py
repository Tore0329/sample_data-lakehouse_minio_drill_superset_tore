import os
import json
import requests

url = "https://sa-mp.im/api/v1/players/get"

resp = requests.get(url)

print(f"{len(resp.json())} ->\n{json.dumps(resp.json(), indent=4)}")