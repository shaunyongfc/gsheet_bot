import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
testspreadsheet = client.open("Octopath WOTV")
sharedspreadsheet = client.open("Ramada Bot")

def get_dfwotv():
    dfwotv = dict()

    df = pd.DataFrame(testspreadsheet.worksheet('WOTV_eq').get_all_records())
    dfwotv['eq'] = df.set_index('EQ Name')

    df = pd.DataFrame(testspreadsheet.worksheet('WOTV_matname').get_all_records())
    dfwotv['mat'] = df.set_index('Material')

    df = pd.DataFrame(testspreadsheet.worksheet('WOTV_vc').get_all_records())
    dfwotv['vc'] = df.set_index('VC Name')

    df = pd.DataFrame(testspreadsheet.worksheet('WOTV_esper').get_all_records())
    dfwotv['esper'] = df.set_index('Esper')

    df = pd.DataFrame(testspreadsheet.worksheet('WOTVGL_esper').get_all_records())
    dfwotv['gl_esper'] = df.set_index('Esper')

    df = pd.DataFrame(sharedspreadsheet.worksheet('WOTV_shortcut').get_all_records())
    dfwotv['shortcut'] = df.set_index('Shortcut')

    df = pd.DataFrame(sharedspreadsheet.worksheet('WOTV_stars').get_all_records())
    dfwotv['stars'] = df
    return dfwotv

dfwotv = get_dfwotv()

def get_df_cotc():
    df_cotc = pd.DataFrame(testspreadsheet.worksheet('COTC_owned').get_all_records())
    df_cotc = df_cotc.set_index('トラベラー')
    return df_cotc

df_cotc = get_df_cotc()
