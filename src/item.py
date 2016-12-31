# coding: cp1250
# Rafal Jasicki

class Item:
    def __init__(self, idx, desc):
        self.idx = idx
        self.desc = desc


class Warehouse:
    def __init__(self, safedb):
        self.data = safedb
