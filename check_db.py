import sqlite3

c = sqlite3.connect('state/ledger.sqlite')
c.row_factory = sqlite3.Row
print('news_items:', c.execute('SELECT COUNT(*) FROM news_items').fetchone()[0])
print('news_ingest events:', c.execute("SELECT COUNT(*) FROM events WHERE kind='news_ingest'").fetchone()[0])
print('predictions:', c.execute('SELECT COUNT(*) FROM predictions').fetchone()[0])
print('paper_only_skip_real_order:', c.execute("SELECT COUNT(*) FROM events WHERE kind='paper_only_skip_real_order'").fetchone()[0])
print('position_opened events:', c.execute("SELECT COUNT(*) FROM events WHERE kind='position_opened'").fetchone()[0])
print('config event:', dict(c.execute("SELECT * FROM events WHERE kind='config' ORDER BY event_time DESC LIMIT 1").fetchone() or {}))