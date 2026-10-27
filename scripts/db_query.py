import sqlite3
import sys

if len(sys.argv) < 2:
    print("usage: python -m scripts.db_query '<sql>'")
    sys.exit(1)

conn = sqlite3.connect("state/ledger.sqlite")
conn.row_factory = sqlite3.Row
for row in conn.execute(sys.argv[1]):
    print(dict(row))