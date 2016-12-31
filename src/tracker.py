# coding: cp1250
# Rafal Jasicki

class Tracker:
    def __init__(self, lenght = 10):
        self.data = {}
        self.l = lenght
        self.known_keys = ["test:name", "author", "publisher",
                "item:name", 'item:public', 'item:private',
                'test:public', 'test:private',
                'pers:name', 'pers:lname', 'ad:main', 'as:addi', 'phone']
        for k in self.known_keys:
            self.data[k] = []

    def __len__(self, key):
        return len(self.data)

    def __getitem__(self, key):
        #print self.data[key]
        return self.data[key]

    def __setitem__(self, key, value):
        #print "TRACKER:", key, '`', value, '`', "known:", key in self.known_keys
        if value == "": return
        if key in self.known_keys:
            if value in self.data[key]:
                self.data[key].pop(self.data[key].index(value))
                self.data[key][0:0] = [value]
                return
            
            if len(self.data[key]) >= self.l:
                self.data[key].pop()
            #print self.data[key]
            self.data[key][0:0] = [value]
            #print self.data[key]

        else:
            self.data[key] = value
    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        try:
            tmp = self.data[key]
            return True
        except:
            return False

    def setLenght(self, l):
        self.l = l
    
