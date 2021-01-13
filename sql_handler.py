import sqlite3

# prototype to add sql application for learning purpose

class MyDB():
    def __init__(self):
        self.conn = sqlite3.connect('mybotdb.db')
        self.cur = conn.cursor()
        try:
            self.cur.execute("""CREATE TABLE msgshortcuts (
                        name text,
                        type text,
                        id integer
                        )""")
        except:
            pass
    def

if __name__ == '__main__':
    conn, cur = db_init()
