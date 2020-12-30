import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

def get_df():
    spreadsheet = client.open("Octopath WOTV")

    df_wotvmats = pd.DataFrame(spreadsheet.worksheet('WOTV_matlist').get_all_records())
    df_wotvmats = df_wotvmats.set_index('EQ Name')

    df_wotvvc = pd.DataFrame(spreadsheet.worksheet('WOTV_vc').get_all_records())
    df_wotvvc = df_wotvvc.set_index('VC Name')

    df_wotvshortcut = pd.DataFrame(spreadsheet.worksheet('WOTV_shortcut').get_all_records())
    df_wotvshortcut = df_wotvshortcut.set_index('Shortcut')

    df_wotvesper = pd.DataFrame(spreadsheet.worksheet('WOTV_esper').get_all_records())
    df_wotvesper = df_wotvesper.set_index('Esper')
    return df_wotvmats, df_wotvvc, df_wotvshortcut, df_wotvesper

df_wotvmats, df_wotvvc, df_wotvshortcut, df_wotvesper = get_df()

def get_df_cotc():
    spreadsheet = client.open("Octopath WOTV")

    df_cotc = pd.DataFrame(spreadsheet.worksheet('COTC_owned').get_all_records())
    df_cotc = df_cotc.set_index('トラベラー')
    return df_cotc

df_cotc = get_df_cotc()
