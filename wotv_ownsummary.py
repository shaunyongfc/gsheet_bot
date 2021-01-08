import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from gsheet_handler import client
ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth', 'Thunder', 'Water', 'Light', 'Dark']
ROLES = ['Slash', 'Pierce', 'Strike', 'Missile', 'Magic', 'Heal', 'Tank']

def main(spreadsheet):
    df_wotvunitcat = pd.DataFrame(spreadsheet.worksheet('WOTV_unitcat').get_all_records())
    df_wotvunitcat = df_wotvunitcat.set_index('Unit')
    list_elements = []
    for element in ELEMENTS:
        df_element = df_wotvunitcat[df_wotvunitcat['Element'] == element]
        list_roles = []
        for role in ROLES:
            df_role = df_element[df_element[role] != '']
            list_units = []
            for index, row in df_role.iterrows():
                if row[role] == 'Y':
                    list_units.append(index)
                else:
                    list_units.append(f"{index} ({row[role]})")
            if len(list_units) > 0:
                list_roles.append(', '.join(list_units))
            else:
                list_roles.append('')
        list_elements.append(list_roles)
    df = pd.DataFrame.from_records(data=list_elements, index=ELEMENTS, columns=ROLES)
    return df

if __name__ == '__main__':
    spreadsheet = client.open("Octopath WOTV")
    worksheet = spreadsheet.worksheet('WOTV_unitsum')
    set_with_dataframe(worksheet, main(spreadsheet), include_index=True)
