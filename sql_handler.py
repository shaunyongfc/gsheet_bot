import sqlite3
import re

# probably better to just use google sheet but forcefully add sql application for learning purpose
class MyDB():
    def __init__(self):
        self.res = re.compile(r'&\w+') # regex for shortcuts
        self.conn = sqlite3.connect('mybotdb.db')
        self.cur = self.conn.cursor()
        try:
            self.cur.execute("""CREATE TABLE msgshortcuts (
                        name text,
                        type integer,
                        id integer
                        )""")
        except:
            pass
    def new_shortcut(self, name, type, id):
        with self.conn:
            self.cur.execute("INSERT INTO msgshortcuts VALUES (:name, :type, :id)",
                            {'name': name, 'type': type, 'id': id})
    def delete_shortcut(self, name):
        with self.conn:
            self.cur.execute("DELETE from msgshortcuts WHERE name = :name",
                            {'name': name})
    def get_shortcut(self, name):
        self.cur.execute(f"SELECT * FROM msgshortcuts WHERE name = :name",
                        {'name': name})
        tuplist = self.cur.fetchall()
        if len(tuplist) == 1:
            tup = tuplist[0]
            if tup[1] == 0: # channel id
                return tup[2]
            elif tup[1] == 1: # user id
                return f"<@{tup[2]}>"
            elif tup[1] == 2: # regular emote
                return f"<:{tup[0]}:{tup[2]}>"
            elif tup[1] == 3: # animated emote
                return f"<a:{tup[0]}:{tup[2]}>"
    def get_all_shortcuts(self):
        self.cur.execute(f"SELECT * FROM msgshortcuts")
        return self.cur.fetchall()
    def msg_process(self, argstr):
        re_matches = self.res.findall(argstr)
        for re_match in re_matches:
            argstr = argstr.replace(re_match, self.get_shortcut(re_match[1:]))
        return argstr

mydb = MyDB()
