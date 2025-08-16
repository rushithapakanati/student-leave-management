# init_db.py
import sqlite3

conn = sqlite3.connect('leaves.db')
c = conn.cursor()

c.execute('DROP TABLE IF EXISTS leaves')
c.execute('''
CREATE TABLE leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    name TEXT NOT NULL,
    reason TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT DEFAULT 'Pending'
)
''')

conn.commit()
conn.close()
print("Database initialized with email column.")
