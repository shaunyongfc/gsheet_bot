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
        self.ids = {
            'WOTV Events': [],
            'FFBE Server': []
        }
        self.sync()
        self.sync_events()
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
        self.rand = pd.DataFrame(ramadaspreadsheet.worksheet('WOTV_rand').get_all_records())

        df_ids = pd.DataFrame(ramadaspreadsheet.worksheet('my_ids').get_all_records())
        for k in self.ids.keys():
            self.ids[k] = df_ids[df_ids['Type'] == k]['ID'].tolist()
    def sync_events(self):
        self.events = pd.DataFrame(ramadaspreadsheet.worksheet('WOTV_events').get_all_records())
    def add_event(self, event):
        ramadaspreadsheet.worksheet('WOTV_events').append_row(event)
        self.sync_events()

dfwotv = DfHandlerWotv()

class DfHandlerGen():
    # Object handling general sheets related operations
    def __init__(self):
        self.sync()
    def sync(self):
        self.shortcuts = pd.DataFrame(ramadaspreadsheet.worksheet('my_shortcuts').get_all_records())
    def add_shortcut(self, *arg):
        ramadaspreadsheet.worksheet('my_shortcuts').append_row(list(arg))
        self.sync()

dfgen = DfHandlerGen()
