from gsheet_handler import client
ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth', 'Thunder', 'Water', 'Light', 'Dark']
ROLES = ['Slash', 'Pierce', 'Strike', 'Missile', 'Magic', 'Heal', 'Tank']

def main():
    spreadsheet = client.open("Octopath WOTV")
    df_wotvunitcat = pd.DataFrame(spreadsheet.worksheet('WOTV_unitcat').get_all_records())
    df_wotvunitcat = df_wotvmats.set_index('Unit')
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
    return list_elements

if __name__ == '__main__':
    print(main())
