import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

spreadsheet = client.open("Octopath WOTV")

df_cotc = pd.DataFrame(spreadsheet.worksheet('COTC_owned').get_all_records())
df_cotc = df_cotc.set_index('トラベラー')

df_wotv = pd.DataFrame(spreadsheet.worksheet('WOTV_matlist').get_all_records())
df_wotv = df_wotv.set_index('EQ Name')
