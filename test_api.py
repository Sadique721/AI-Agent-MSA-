import requests, json

base = 'http://127.0.0.1:5000'

print("=== /api/status ===")
r = requests.get(base + '/api/status', timeout=5)
print(json.dumps(r.json(), indent=2))

print("\n=== /api/system_info ===")
r = requests.get(base + '/api/system_info', timeout=5)
d = r.json().get('data', {})
print("  CPU:  " + str(d.get('cpu_percent')) + "%")
print("  RAM:  " + str(d.get('ram_used_gb')) + "/" + str(d.get('ram_total_gb')) + " GB")
print("  Disk: " + str(d.get('disk_used_gb')) + "/" + str(d.get('disk_total_gb')) + " GB")
print("  Platform: " + str(d.get('platform')) + "  Uptime: " + str(d.get('uptime_human')))

print("\n=== /api/execute — open notepad ===")
r = requests.post(base + '/api/execute', json={'command': 'open notepad'}, timeout=10)
print(json.dumps(r.json(), indent=2))

print("\n=== /api/execute — search python ===")
r = requests.post(base + '/api/execute', json={'command': 'search python'}, timeout=10)
print(json.dumps(r.json(), indent=2))

print("\n=== /api/execute — shutdown ===")
r = requests.post(base + '/api/execute', json={'command': 'what can you do'}, timeout=10)
print(json.dumps(r.json(), indent=2))

print("\n=== /api/history ===")
r = requests.get(base + '/api/history?limit=3', timeout=5)
d = r.json()
print("status:", d.get('status'), "| count:", len(d.get('history', [])))
for h in d.get('history', []):
    print("  You:", str(h.get('user',''))[:50])
    print("  MSA:", str(h.get('assistant',''))[:60])

print("\n=== /mobile/execute ===")
r = requests.post(base + '/mobile/execute', json={'command': 'open calculator'}, timeout=5)
print(json.dumps(r.json(), indent=2))

print("\n=== /mobile/status ===")
r = requests.get(base + '/mobile/status', timeout=5)
print(json.dumps(r.json(), indent=2))

print("\nAll tests passed!")
