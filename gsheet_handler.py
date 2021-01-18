import gspread, re
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
myspreadsheet = client.open("Octopath WOTV")
ramadaspreadsheet = client.open("Ramada Bot")

class DfHandlerWotv():
    # Object handling WOTV sheets related operations
    def __init__(self):
        self.sync()
    def sync(self):
        df = pd.DataFrame(myspreadsheet.worksheet('WOTV_eq').get_all_records())
        self.eq = df.set_index('EQ Name')

        df = pd.DataFrame(myspreadsheet.worksheet('WOTV_vc').get_all_records())
        self.vc = df.set_index('VC Name')

        df = pd.DataFrame(myspreadsheet.worksheet('WOTV_esper').get_all_records())
        self.esper = df.set_index('Esper')

        #df = pd.DataFrame(myspreadsheet.worksheet('WOTVGL_esper').get_all_records())
        #self.glesper = df.set_index('Esper')

        df = pd.DataFrame(ramadaspreadsheet.worksheet('WOTV_matname').get_all_records())
        self.mat = df.set_index('Material')

        df = pd.DataFrame(ramadaspreadsheet.worksheet('WOTV_shortcut').get_all_records())
        self.shortcut = df.set_index('Shortcut')

        self.stars = pd.DataFrame(ramadaspreadsheet.worksheet('WOTV_stars').get_all_records())

dfwotv = DfHandlerWotv()

class DfHandlerGen():
    # Object handling general sheets related operations
    def __init__(self):
        self.res = re.compile(r'&\w+') # regex for shortcuts
        self.sync()
    def sync(self):
        self.shortcuts = pd.DataFrame(ramadaspreadsheet.worksheet('my_shortcuts').get_all_records())
    def add_shortcut(self, *arg):
        if len(arg) == 3:
            try:
                int(arg[2])
                ramadaspreadsheet.worksheet('my_shortcuts').append_row(list(arg))
                self.sync()
                return 'Added.'
            except ValueError:
                return 'Non-integer id.'
        else:
            return 'Incorrect arguments.'
    def get_shortcut(self, name):
        row_index = self.shortcuts[self.shortcuts['Name'] == name].index.tolist()[0]
        row = self.shortcuts.iloc[row_index]
        if row['Type'] == 'channel':
            return row['id']
        elif row['Type'] == 'user':
            return f"<@{row['id']}>"
        elif row['Type'] == 'emote':
            return f"<:{row['Name']}:{row['id']}>"
        elif row['Type'] == 'aemote':
            return f"<a:{row['Name']}:{row['id']}>"
        elif row['Type'] == 'role':
            return f"<@&{row['id']}>"
    def msg_process(self, argstr):
        re_matches = self.res.findall(argstr)
        for re_match in re_matches:
            try:
                argstr = argstr.replace(re_match, self.get_shortcut(re_match[1:]))
            except IndexError:
                pass
        return argstr

dfgen = DfHandlerGen()

class DfHandlerCotc():
    # Object handling COTC sheets related operations
    def __init__(self):
        self.sync()
    def sync(self):
        df_cotc = pd.DataFrame(myspreadsheet.worksheet('COTC_owned').get_all_records())
        self.cotc = df_cotc.set_index('トラベラー')

dfcotc = DfHandlerCotc()
