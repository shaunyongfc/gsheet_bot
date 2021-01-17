import pandas as pd
import gspread
from gsheet_handler import  myspreadsheet

SHARDS_REQ = {
    'UR+': [40, 80, 120, 160, 200],
    'UR': [40, 80, 120, 160, 200],
    'SSR': [20, 40, 80, 160, 200],
    'EX': [80, 120, 200]
    }
STAGE_NAME = ['LB +0', 'LB +1', 'LB +2', 'LB +3', 'LB +4', 'LB +5', 'EX 19', 'EX 22', 'EX 25']
LB_SUPPRESS = 3

# WIP to process a personal sheet of unit data into progress prediction

class Unit:
    def __init__(self, rarity='UR', plus=0, shards=0):
        self.rarity = rarity
        self.plus = plus
        self.shards = shards
        self.barracks = 0
        self.hq = 0
        self.advance()
    def advance(self):
        if self.plus < 5:
            self.checkpoint = SHARDS_REQ[self.rarity][self.plus]
        elif self.plus == 8:
            self.checkpoint = 0
        else:
            self.checkpoint = SHARDS_REQ['EX'][self.plus - 5]
    def gain_shard(self, number):
        if self.plus < 8:
            self.shards += number
            if self.shards >= self.checkpoint:
                self.shards -= self.checkpoint
                self.plus += 1
                self.advance()
                if self.plus >= LB_SUPPRESS:
                    return 1
        return 0

class Roster:
    def __init__(self, unit_list, freq=1):
        self.bcount = 0
        self.hqcount = 0
        self.day_count = 0
        self.freq = freq
        self.units = unit_list
        self.gains = dict()
        for k in unit_list:
            self.gains[k] = [0, 0]
    def hq_print(self):
        print(f'HQ ({self.hqcount}/10): {self.hqlist}')
    def b_print(self):
        print(f'Barracks ({self.bcount}/5): {self.blist}')
    def daily(self):
        change_list = []
        for k, v in self.units.items():
            if v.gain_shard(sum(self.gains[k])):
                change_list.append(k)
        return change_list
    def progress(self):
        change_list = []
        while True:
            for _ in range(self.freq):
                self.day_count += 1
                change_list += self.daily()
            if len(change_list) > 0:
                break
        print(f'Day {self.day_count}:')
        for name in change_list:
            print(f'   {name} -> {STAGE_NAME[self.units[name].plus]}!')
        return self.day_count
    def progress_target(self, name, target):
        while self.units[name].plus < target:
            self.progress()
