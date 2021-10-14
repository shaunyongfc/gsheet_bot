import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json',
                                                         scope)
client = gspread.authorize(creds)
wotvspreadsheet = client.open('My WOTV')
ramadaspreadsheet = client.open('Ramada Bot')


class DfHandlerWotv():
    """Object to handle WOTV sheets related operations."""
    def __init__(self):
        """Object initialisation."""
        # Dictionary to save various IDs.
        self.ids = {
            'WOTV Events': [],
            'FFBE Server': [],
            'Newsfeed': [],
        }
        # Initial synchronisations.
        self.sync()
        self.sync_events()

    def sync(self):
        """"To construct or refresh tables from Google sheets."""
        # Equipment data.
        df = pd.DataFrame(
            wotvspreadsheet.worksheet('WOTV_eq').get_all_records())
        self.eq = df.set_index('EQ Name')
        # Vision card data.
        df = pd.DataFrame(
            wotvspreadsheet.worksheet('WOTV_vc').get_all_records())
        self.vc = df.set_index('VC Name')
        # Esper data.
        df = pd.DataFrame(
            wotvspreadsheet.worksheet('WOTV_esper').get_all_records())
        self.esper = df.set_index('Esper')
        # Material name table.
        df = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_matname').get_all_records())
        self.mat = df.set_index('Material')
        # Shortcut table.
        df = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_shortcut').get_all_records())
        self.shortcut = df[df['Type'] == 'shortcut']\
                            .drop('Type', axis=1).set_index('Shortcut')
        self.replace = df[df['Type'] == 'replace']\
                            .drop('Type', axis=1).set_index('Shortcut')
        # Text table.
        self.text = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_text').get_all_records())
        # Fluff tables.
        self.stars = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_stars').get_all_records())
        self.rand = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_rand').get_all_records())
        # Import ids from separate file.
        df_ids = pd.DataFrame(
            ramadaspreadsheet.worksheet('my_ids').get_all_records())
        for k in self.ids.keys():
            self.ids[k] = df_ids[df_ids['Type'] == k]['ID'].tolist()

    def sync_events(self):
        """Event data.
        Separated because it is updated more frequently.
        """
        # Event data.
        self.events = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_events').get_all_records())

    def add_event(self, event):
        """Used for when adding events via discord command."""
        ramadaspreadsheet.worksheet('WOTV_events').append_row(event)
        self.sync_events()


class DfHandlerGen():
    """Object handling general sheets related operations."""
    def __init__(self):
        """Object initialisation."""
        # Initial synchronisation.
        self.sync()

    def sync(self):
        """"To construct or refresh tables from Google sheets."""
        # Sheet for personal shortcuts.
        self.shortcuts = pd.DataFrame(
            ramadaspreadsheet.worksheet('my_shortcuts').get_all_records())

    def add_shortcut(self, *arg):
        """Used for when adding shortcuts via discord command."""
        ramadaspreadsheet.worksheet('my_shortcuts').append_row(list(arg))
        self.sync()
