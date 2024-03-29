import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json',
                                                         scope)
client = gspread.authorize(creds)
wotvspreadsheet = client.open('Ildyra Bot')
ramadaspreadsheet = client.open('Ramada Bot')


class DfHandlerWotv():
    """Object to handle WOTV sheets related operations."""
    def __init__(self):
        """Object initialisation."""
        # Dictionary to save various IDs.
        self.ids = {
            'WOTV Events': [],
            'FFBE Server': [],
            'WOTV Newsfeed': [],
            'WOTV Sync': [],
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
        # Trust master data.
        df = pd.DataFrame(
            wotvspreadsheet.worksheet('WOTV_tm').get_all_records())
        self.tm = df.set_index('Unit Name')
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
        self.eq_type = df[df['Type'] == 'eq_type']\
                            .drop('Type', axis=1).set_index('Shortcut')
        self.w_type = df[df['Type'] == 'w_type']\
                            .drop('Type', axis=1).set_index('Shortcut')
        self.removal = df[df['Type'] == 'removal']\
                            .drop('Type', axis=1).set_index('Shortcut')
        # Text table.
        self.text = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_text').get_all_records())
        # Fluff tables.
        self.stars = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_stars').get_all_records())
        self.rand = pd.DataFrame(
            ramadaspreadsheet.worksheet('WOTV_rand').get_all_records())
        # Import various ids.
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
        # Sheet for tags.
        self.tags = pd.DataFrame(
            ramadaspreadsheet.worksheet('my_tags').get_all_records()
        )
        self.tags["Tag"] = self.tags["Tag"].astype(str)
        self.tags_last = len(self.tags) + 1
        # Sheet for ids.
        self.ids = pd.DataFrame(
            ramadaspreadsheet.worksheet('my_ids').get_all_records())
        self.ids['ID'] = self.ids['ID'].astype('int64')

    def add_shortcut(self, *arg):
        """Used for when adding shortcuts via discord command."""
        ramadaspreadsheet.worksheet('my_shortcuts').append_row(list(arg))
        self.sync()

    def sync_tags(self, clean=False):
        """Sync local Data to Google sheets."""
        df = self.tags.copy()
        df['User'] = df['User'].apply(str)
        try:
            if clean:
                ramadaspreadsheet.values_clear(f"my_tags!A2:E{self.tags_last}")
            self.tags_last = len(self.tags) + 1
            set_with_dataframe(
                ramadaspreadsheet.worksheet('my_tags'),
                df,
                include_index=False
            )
            return 1
        except gspread.exceptions.APIError as e:
            return e
