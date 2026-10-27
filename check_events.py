import sqlite3

c = sqlite3.connect('state/ledger.sqlite')
c.row_factory = sqlite3.Row

print('=== Events (all kinds) ===')
for r in c.execute('SELECT kind, COUNT(*) as cnt FROM events GROUP BY kind ORDER BY cnt DESC'):
    print(f'  {r["kind"]}: {r["cnt"]}')

print()
print('=== Events (recent) ===')
for r in c.execute('SELECT event_time, kind, payload FROM events ORDER BY event_time DESC LIMIT 20'):
    print(r['event_time'], r['kind'], r['payload'][:120] if r['payload'] else '')