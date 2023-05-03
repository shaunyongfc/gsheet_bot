import pandas as pd
import os
import re
from PIL import Image, ImageDraw, ImageFont

# Get data from google sheet

FOLDER = "wotv_esper_chart"
E_LIST = ["Neutral", "Fire", "Ice", "Wind", "Earth", "Thunder", "Water",
    "Light", "Dark", "Tank"]
A_LIST = ["None", "Slash", "Pierce", "Strike", "Missile", "Magic"]
P_LIST = ["Slash", "Pierce", "Strike", "Missile"]
SPECIAL_BUFFS = (
    # Column, Buff Name, Threshold, File Name
    ("RES Up", "Human", 0, "human_res"),
    ("RES Up", "Single", 0, "single"),
    ("RES Up", "Area", 0, "area"),
    ("Stat Up", "LUCK%", 0, "luck"),
    ("Stat Up", "Accuracy", 15, "accuracy"),
    ("Stat Up", "Evasion", 15, "evasion"),
    ("Stat Up", "Reaction Block", 0, "reaction"),
    ("Stat Up", "Cast Time", 0, "cast"),
    ("Stat Up", "Evoke", 0, "evoke"),
    ("Stat Up", "Initial AP", 0, "initial_ap"),
    ("Stat Up", "Crit Rate", 20, "crit"),
    ("Stat Up", "Crit Damage", 15, "crit_damage"),
    ("Stat Up", "Crit Evade", 15, "crit_evade"),
    ("Stat Up", "ATK%", 15, "atk"),
    ("Stat Up", "MAG%", 15, "mag"),
    ("Stat Up", "DEF", 0, "def"),
    ("Stat Up", "SPR", 0, "spr"),
    ("Stat Up", "HP%", 0, "hp"),
    ("Stat Up", "TP%", 0, "tp"),
    ("Stat Up", "AP%", 0, "ap"),
)
RESIST_BUFFS = (
    # Attack Type, File Name
    ("Slash", "c1"),
    ("Pierce", "c2"),
    ("Strike", "c3"),
    ("Missile", "c4"),
    ("Magic", "c5"),
)
# ICON
ICON_SIZE = 100
ICON_ESPER_SIZE = 90
ICON_ESPER_MARGIN = 5
ICON_ELE_SIZE = 30
ICON_AGI_SIZE = 30
ICON_AGI_FONT = 24
ICON_BUFF_SIZE = 20
ICON_RES_SIZE = 25
ICON_SHIELD_SIZES = (15, 20) # X: 15/25 -> 30/25; Y: 5/25 -> 25/25
ICON_SHIELD_X = 15
ICON_SHIELD_Y = 5

# CHART
BORDER_SIZE = 5
ICON_STACK = 3
HEADER_SIZE = 100
HEADER_MARGIN = (ICON_SIZE * ICON_STACK - HEADER_SIZE) // 2
ROWS = ("r00", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9")
COLUMNS = ("c6", "c1", "c2", "c3", "c4", "c5")
PANEL_SIZE = ICON_SIZE * ICON_STACK + BORDER_SIZE
FULL_WIDTH = HEADER_SIZE + BORDER_SIZE + PANEL_SIZE * len(COLUMNS)
FULL_HEIGHT = HEADER_SIZE + BORDER_SIZE + PANEL_SIZE * len(ROWS)

my_font = ImageFont.truetype('Arial.ttf', ICON_AGI_FONT)
revalues = re.compile(r'-?\d+$')
df = pd.read_excel(os.path.join(FOLDER, "esper.xlsx"))


def process_esper(df_row):
    """
    Read data for 1 esper and add rarity frame, element agi and
    specific buff icons.
    """
    im_name = f"{df_row['English']}.webp"
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE))
    # Esper base
    base = Image.open(os.path.join(FOLDER, "esper_base", im_name))
    base = base.resize((ICON_ESPER_SIZE, ICON_ESPER_SIZE))
    image.paste(base, (ICON_ESPER_MARGIN, ICON_ESPER_MARGIN))
    # Rarity frame
    rarity = Image.open(os.path.join(
        FOLDER, f"rarity_{df_row['Rarity'].lower()}.png"
    ))
    rarity = rarity.resize((ICON_SIZE, ICON_SIZE))
    image.paste(rarity, (0, 0), rarity)
    # Element
    ele = Image.open(os.path.join(
        FOLDER, f"r{E_LIST.index(df_row['Element'])}.png"
    ))
    ele = ele.resize((ICON_ELE_SIZE, ICON_ELE_SIZE))
    image.paste(ele, (0, 0), ele)
    # Agility square
    agi = Image.open(os.path.join(FOLDER, "agi.png"))
    agi = agi.resize((ICON_AGI_SIZE, ICON_AGI_SIZE))
    image.paste(agi, (ICON_SIZE - ICON_AGI_SIZE, 0))
    square = Image.new("RGBA", (ICON_AGI_SIZE, ICON_AGI_SIZE), (0, 0, 0))
    mask = Image.eval(square.getchannel('A'), lambda a: 144)
    image.paste(square, (ICON_SIZE - ICON_AGI_SIZE, 0), mask)
    # Agility text
    image_draw = ImageDraw.Draw(image)
    image_draw.text((ICON_SIZE - ICON_AGI_SIZE + 1, 1), str(df_row['AGI']),
        fill=(255, 255, 255), font=my_font
    )
    # Special icons
    icon_x = 0
    for column, buff, threshold, fname in SPECIAL_BUFFS:
        c_buffs = str(df_row[column]).split(" / ")
        for c_buff in c_buffs:
            if buff in c_buff and int(revalues.findall(c_buff)[0]) >= threshold:
                icon = Image.open(os.path.join(FOLDER, f"eff_{fname}.png"))
                icon = icon.resize((ICON_BUFF_SIZE, ICON_BUFF_SIZE))
                image.paste(icon, (icon_x, ICON_SIZE - ICON_BUFF_SIZE), icon)
                icon_x += ICON_BUFF_SIZE
        if icon_x >= ICON_SIZE:
            break
    # Attack resist icons
    icon_y = ICON_ELE_SIZE + ICON_RES_SIZE
    for buff, fname in RESIST_BUFFS:
        c_buffs = str(df_row["RES Up"]).split(" / ")
        for c_buff in c_buffs:
            if buff in c_buff:
                icon = Image.open(os.path.join(FOLDER, f"{fname}.png"))
                icon = icon.resize((25, 25))
                image.paste(icon, (0, icon_y), icon)
                # Shield icon to indicate resist
                shield = Image.open(os.path.join(FOLDER, "shield.png"))
                shield = shield.resize(ICON_SHIELD_SIZES)
                image.paste(shield, (ICON_SHIELD_X, icon_y + ICON_SHIELD_Y), shield)
                icon_y -= ICON_RES_SIZE
        if icon_y <= ICON_RES_SIZE:
            break
    # Save and report
    image.save(os.path.join(FOLDER, "esper_processed", im_name))
    print(f"{im_name} processed.")


def make_chart():
    """
    Create chart from processed esper icons.
    """
    chart = Image.new("RGBA", (FULL_WIDTH, FULL_HEIGHT), (255, 255, 255)
    )
    chart_draw = ImageDraw.Draw(chart)
    # Draw background and borders and headers
    ## Horizontal - borders
    for i in range(10):
        y = HEADER_SIZE + PANEL_SIZE * i
        if i % 2:
            chart_draw.rectangle(
                (0, y, FULL_WIDTH, y + PANEL_SIZE),
                fill=(230, 230, 230)
            )
        header = Image.open(os.path.join(FOLDER, f"{ROWS[i]}.png"))
        header = header.resize((HEADER_SIZE, HEADER_SIZE))
        chart.paste(header, (0, y + HEADER_MARGIN), header)
    ## Vertical
    for i in range(6):
        x = HEADER_SIZE + PANEL_SIZE * i
        if i % 2:
            chart_draw.rectangle(
                (x, 0, x + PANEL_SIZE, FULL_HEIGHT),
                fill=(230, 230, 230)
            )
        chart_draw.rectangle(
            (x, 0, x + BORDER_SIZE, FULL_HEIGHT),
            fill=(0, 0, 0)
        )
        header = Image.open(os.path.join(FOLDER, f"{COLUMNS[i]}.png"))
        header = header.resize((HEADER_SIZE, HEADER_SIZE))
        chart.paste(header, (x + HEADER_MARGIN, 0), header)
    ## Horizontal borders
    for i in range(10):
        y = HEADER_SIZE + PANEL_SIZE * i
        chart_draw.rectangle(
            (0, y, FULL_WIDTH, y + BORDER_SIZE),
            fill=(0, 0, 0)
        )
    # Element + Attack Type
    ## Generate list of lists
    esper_lists = [[[] for _ in range(6)] for _ in range(10)]
    for _, df_row in df.iterrows():
        esper_tuple = (df_row['English'], df_row["AGI"])
        atk_ups = str(df_row["ATK Up"])
        a_up = 0
        e_up = 0
        for a_buff in A_LIST:
            if a_buff in atk_ups:
                a_up = A_LIST.index(a_buff)
                break
        for e_buff in E_LIST:
            if e_buff in atk_ups:
                e_up = E_LIST.index(e_buff)
                break
        if a_up != 0 or e_up != 0:
            esper_lists[e_up][a_up].append(esper_tuple)
        if "Human" in str(df_row["Killer"]):
            esper_lists[0][0].append(esper_tuple)
        c_buffs = str(df_row["Stat Up"]).split(" / ")
        def_up = 0
        spr_up = 0
        for c_buff in c_buffs:
            if "DEF" in c_buff:
                def_up = int(revalues.findall(c_buff)[0])
            elif "SPR" in c_buff:
                spr_up = int(revalues.findall(c_buff)[0])
                if spr_up >= 10:
                    esper_lists[9][5].append(esper_tuple)
        c_buffs = str(df_row["RES Up"]).split(" / ")
        type_assigned = 0
        for c_buff in c_buffs:
            for buff in P_LIST:
                if buff in c_buff:
                    if def_up + int(revalues.findall(c_buff)[0]) >= 25:
                        esper_lists[9][A_LIST.index(buff)].append(esper_tuple)
                        type_assigned = 1
            if "Magic" in c_buff and spr_up < 10:
                if int(revalues.findall(c_buff)[0]) >= 20:
                    esper_lists[9][5].append(esper_tuple)
        if def_up >= 10 and not type_assigned:
            esper_lists[9][0].append(esper_tuple)
    # Sort by AGI and check total espers per panel
    for i in range(10):
        for j in range(6):
            esper_lists[i][j].sort(key=lambda a: a[1], reverse=True)
            print(len(esper_lists[i][j]), end=" ")
        print()

    # Paste esper icons
    for i in range(10):
        for j in range(6):
            x = HEADER_SIZE + PANEL_SIZE * j + BORDER_SIZE
            y = HEADER_SIZE + PANEL_SIZE * i + BORDER_SIZE
            x1 = 0
            y1 = 0
            for esper, agi in esper_lists[i][j]:
                icon = Image.open(os.path.join(FOLDER, "esper_processed",
                    f"{esper}.webp"))
                chart.paste(icon, (x + x1, y + y1), icon)
                y1 += ICON_SIZE
                if y1 == ICON_SIZE * ICON_STACK:
                    y1 = 0
                    x1 += ICON_SIZE
                if x1 == ICON_SIZE * ICON_STACK:
                    break

    # Save and report
    chart.save(os.path.join(FOLDER, "wotv_esper_chart.png"))
    print("wotv_esper_chart.png saved.")


if __name__ == "__main__":
    for _, df_row in df.iterrows():
        process_esper(df_row)
    make_chart()
