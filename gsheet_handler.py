import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

def get_dfwotv():
    dfwotv = dict()
    spreadsheet = client.open("Octopath WOTV")

    df = pd.DataFrame(spreadsheet.worksheet('WOTV_eq').get_all_records())
    dfwotv['eq'] = df.set_index('EQ Name')

    df = pd.DataFrame(spreadsheet.worksheet('WOTV_matname').get_all_records())
    dfwotv['mat'] = df.set_index('Material')

    df = pd.DataFrame(spreadsheet.worksheet('WOTV_vc').get_all_records())
    dfwotv['vc'] = df.set_index('VC Name')

    df = pd.DataFrame(spreadsheet.worksheet('WOTV_shortcut').get_all_records())
    dfwotv['shortcut'] = df.set_index('Shortcut')

    df = pd.DataFrame(spreadsheet.worksheet('WOTV_esper').get_all_records())
    dfwotv['esper'] = df.set_index('Esper')

    df = pd.DataFrame(spreadsheet.worksheet('WOTVGL_esper').get_all_records())
    dfwotv['gl_esper'] = df.set_index('Esper')
    return dfwotv

dfwotv = get_dfwotv()

def get_df_cotc():
    spreadsheet = client.open("Octopath WOTV")

    df_cotc = pd.DataFrame(spreadsheet.worksheet('COTC_owned').get_all_records())
    df_cotc = df_cotc.set_index('トラベラー')
    return df_cotc

df_cotc = get_df_cotc()
