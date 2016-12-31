# coding: cp1250
# Rafał Jasicki


# wlaczyc wysylanie wiadomosci!

import termdb
from os import sep
import os, pprint, Queue


class safedb:
    def __init__(self, max_operations = 80000):
        self.dbA = None
        self.dbB = None
        self.operations = 0
        self.max_operations = max_operations # liczba operacji po której dojdzie do synchronizacji
        self.max_counter = 80000 
        self.last_error = None
        self.not_tracked_items = ['Test: arkusz']#, 'Test: klucz']
        self.app = None
        self.keys_to_update = [] # czy napewno tutaj? może przy tworzeniu/wczytywaniu pliku?
        self.wiki_updated_queue = Queue.Queue()


    def tryFile(self, file_name, default_path = True):
        assert isinstance(file_name, str)
        if default_path:
            file_name = 'data' + sep + file_name
        if os.path.isdir(file_name):
            print "E:znaleziono katalog!"
            self.last_error = "Katalog w miejscu pliku konfiguracyjnego"
            return False

        if os.path.isfile(file_name):
            print "plik znaleziony"
            self.loadFile(file_name, False)
            return True

        self.last_error = "Brak pliku konfiguracyjnego"
        return False

            



    def loadFile(self, file_name, default_path = True):
        assert isinstance(file_name, str)
        if default_path:
            file_name = 'data' + sep + file_name
        try: 
            self.info = termdb.termdb(file_name)
        except:
            self.last_error = "Nie mozna zaladowac pliku INFO"

        try:
            self.dbA = termdb.termdb(self.info['#A'])
        except:
            print "Nie mozna zaladowac pliku A, sprawdzanie domyslnej lokacji"
            self.dbA = termdb.termdb(file_name + "A", 1000)
        try:
            self.dbB = termdb.termdb(self.info['#B'])
        except:
            print "Nie mozna zaladowac pliku B, sprawdzanie domyslnej lokacji"
            self.dbB = termdb.termdb(file_name + "B", 1000)
        
        if self.info['#last'] == 'A':
            self.checkFiles(good = self.dbA, bad = self.dbB)
        else:
            self.checkFiles(good = self.dbB, bad = self.dbA)        

        self.updateFile()
        print self["KEYS_TO_UPDATE"]
        return True
    

    def checkFiles(self, good, bad):
        for k in good.keys():
            try:
                if bad[k] != good[k]:
                    print "blad na kluczu:", k
                    print bad[k], " -- zamiast -- ", good[k]
                    bad[k] = good[k]
            except:
                print "blad na kluczu:", k
                print "brak klucza -- ", good[k]
                bad[k] = good[k]

        bad.sync()
        self.info['#last'] = 'A'
        self.info.sync()



    def printData(self):
        print "============================== INFO ===="
        for k in self.info.keys():
            print k, self.info[k]

        print "================================ db ===="

        for k in self.dbA.keys():
            print " Klucz  :", k
            print " Wartosc: ", self.dbA[k]
            

    def createFile(self, file_name, default_path = True):
        assert isinstance(file_name, str)
        if default_path:
            file_name = 'data' + sep + file_name

        # sprawdzic czy mozna utworzyc plik, czy nie ma tam pliku
        self.info = termdb.termdb(file_name, 1000)
        self.info.clear()

        self.dbA = termdb.termdb(file_name + "A", 1000)
        self.dbB = termdb.termdb(file_name + "B", 1000)
        self.dbA.clear()
        self.dbB.clear()

        self.info['#A'] = file_name + "A"
        self.info['#B'] = file_name + "B"

        self.info['#counter'] = 0

        self.dbA['#counter'] = 0
        self.dbB['#counter'] = 0
        
        self.info['#last'] = 'A'
        self.sync()
        self.updateFile()
            
        return True

    
    def __len__(self, key):
        return len(self.dbA)

    def __getitem__(self, key):
        return self.dbA[key]

    def __setitem__(self, key, value):
        print "safedb.__setitem__:", key, value
        if key[:5] in ["TEST#", "ITEM#", "GROUP"]:
            print "safedb.__setitem__: key should be reported"
            assert(self.app)
            changedValue = True
            try:
                # title change
                if key[:5] == "TEST#" and self[key]["test:name"] != value["test:name"]:
                    print "safedb.__setitem__: test name changed"
                    self.keys_to_update.append("GROUP##" + value['group'])
                # title or category in nontest item change
                elif key[:5] == "ITEM#" and not value['test'] and \
                    (self[key]["item:name"] != value["item:name"] or self[key]['category'] != value['category']):
                    print "safedb.__setitem__: item name or category changed"
                    self.keys_to_update.append(value['category'])
                
                # other change
                if self[key] == value:
                    changedValue = False
                else:
                    print key, "safedb.__setitem__: value changed !!!!!"
            except:
                print key, "safedb.__setitem__: new value !!!!!"
                if key[:5] == "ITEM#" and not value['test']:
                    self.keys_to_update.append(value['category'])
                    print key, "safedb.__setitem__: new non-test item !!!!!"

            if changedValue:
                if key not in self.keys_to_update:
                    self.keys_to_update.append(key)

        self.dbA[key] = value
        self.dbB[key] = value
        self.__newOperation__()



    def __newOperation__(self):
        self.operations += 1
        if self.operations > self.max_operations:
            self.operations = 0
            #self.sync() # NO AUTOMATIC SYNC!!!      

    def __delitem__(self, key):
        del self.dbA[key]
        del self.dbB[key]
        self.__newOperation__()

    def __contains__(self, key):
        try:
            tmp = self.dbA[key]
            return True
        except:
            return False

    def append(self, key, value, sort = False):
        l = self[key]
        l.append(value)
        if sort:
            l.sort()
        self[key] = l


    def sync(self):
        self.raiseCounter()
        tmpList = []
        print "safedb.sync keys_to_update:", self.keys_to_update
        page_content = None
        for key in self.keys_to_update:
            if key[:4] == "ITEM":
                if self[key]['test'] != "":
                    key = self[key]['test']

            if key not in tmpList:
                tmpList.append(key)


        ### Tą linijkę KONIECZNIE usunąć!!!
        #tmpList = []
        ### Tą linijkę KONIECZNIE usunąć!!!
        
        self.keys_to_update = []


        keys = self["KEYS_TO_UPDATE"]
        done = 0
        while not self.wiki_updated_queue.empty():
            self.wiki_updated_queue.get()
            done += 1
        keys = keys[done:]

        self["KEYS_TO_UPDATE"] = keys + tmpList
        
        print "safedb.sync(): tmpList:", tmpList
        
        self.info['#last'] = 'B'
        self.info.sync()
        self.dbA.sync()
        self.info['#last'] = 'A'
        self.info.sync()
        self.dbB.sync()
        
        for key in tmpList:
            self.createWikiMessage(key)


    def createWikiMessage(self, key, page_content = None):
        print "safedb.createWikiMessage(): key:", key
        if key[:3] == "del":
            action = 'page_del'
            value = {'id': key[3:]}
        else:
            action = 'page_save'

            if key in self['#ITEM_TYPE_LIST_2']:
                page_content = {'id': 'category'}
                for category in self['#ITEM_TYPE_LIST_2']:
                    page_content[category] = []
                for i_id in self["#ITEM_LIST"]:
                    item = self[i_id]
                    if not item['test']:
                        page_content[item['category']].append((i_id, item['item:name']))

                value = page_content
                        

            elif key[:5] == "GROUP":
                page_content = {'id': "group"}
                for group in self['#TEST_GROUP_LIST']:
                    page_content[group] = []
                for t_id in self['#TEST_LIST']:
                    page_content[self[t_id]['group']].append((t_id, self[t_id]['test:name']))
                value = page_content
            else:    
                value = self[key]

                if value['ID'][:4] == "TEST":
                    tmp_list = []
                    for i_id in value['items']:
                        tmp_list.append(self[i_id])

                    value['items'] = tmp_list

        
        try:
            print "safedb.createWikiMessage(): message:", (action, value)
            self.app.wiki_thread.ioq.put((action, value))
        except Exception, e:
            print "No wiki_thread !?", e


    def raiseCounter(self):
        if self.info['#counter'] >= self.max_counter:
            self.info['#counter'] = 0
            self.dbA['#counter'] = 0
            self.dbB['#counter'] = 0
        else:
            self.info['#counter'] += 1
            self.dbA['#counter'] += 1
            self.dbB['#counter'] += 1            


    def closeFile(self):
        self.sync()
        self.dbA = None
        self.dbB = None
        self.operations = 0


    def updateFile(self):
        self.__ver__ = "1.23"
        try:
            file_ver = self['#version']
        except:
            file_ver = "new"
            

            if file_ver == "new":
                self['#TEST_COUNT'] = 1000
                self['#TEST_LIST'] = []
                self['#ITEM_COUNT'] = 1000
                self['#ITEM_LIST'] = []

                self['#PERS_COUNT'] = 1000
                self['#PERS_LIST'] = []
                
                self['#wiki-path'] = """http://127.0.0.1/dokuwiki/"""
                self['#wiki-login'] = "automata"
                self['#wiki-pass'] = "test1auto"
                self['#TEST_GROUP_LIST'] = ["Inne"]
                self['GROUP##Inne'] = []

                build_list = []
                tmp = ["podręcznik", "instrukcja", "klucz", "arkusz", "wersja komputerowa", "program obliczeniowy", "pomoce", "inne"]
                for s in tmp:
                    build_list.append("Test: " + s)
                    

                self['#ITEM_TYPE_LIST_1'] = map(lambda x: x.decode("cp1250").encode("UTF-8"), build_list)

                build_list = ["Książka",
                              "Książka z CD",
                              "Audio-Video: CD-ROM",
                              "Audio-Video: DVD",
                              "Audio-Video: VHS",
                              "Audio-Video: kaseta audio",
                              "Program",
                              "Inne"]
                self['#ITEM_TYPE_LIST_2'] = map(lambda x: x.decode("cp1250").encode("UTF-8"), build_list)

                self["KEYS_TO_UPDATE"] = []

                self.regenerateWikiPages()
                        
            
        print "data file version:", file_ver
        if file_ver != self.__ver__:

            self.regenerateWikiPages()

        self.sync()
        # last
        self['#version'] = self.__ver__
        self.sync()
        


    def deleteTest(self, t_id):
        test = self[t_id]
        items = []
        for i_id in test['items']:
            self.deleteItem(i_id)
            items.append(i_id)
        tests = self['#TEST_LIST']
        tests.pop(tests.index(t_id))
        self['#TEST_LIST'] = tests

        group = test['group']
        glist = self["GROUP##" + group]
        glist.pop(glist.index(t_id))
        if group != "Inne" and len(glist) == 0:
            del self["GROUP##" + group]
            groups = self['#TEST_GROUP_LIST']
            groups.pop(groups.index(group))
            self['#TEST_GROUP_LIST'] = groups
        else:
            self["GROUP##" + group] = glist
        #if t_id in self.keys_to_update:
        self.keys_to_update.append("del" + t_id)
        #del self[t_id]
        self.sync()
        
        return (t_id, items)

    def deleteItem(self, i_id, sync = False):
        ### niemożliwe jeśli coś wypożyczone
        if self[i_id]['test'] != "":
            self.keys_to_update.append(self[i_id]['test'])
            test = self[self[i_id]['test']]
            test['items'].pop(test['items'].index(i_id))
            self[test['ID']] = test
        else:
            self.keys_to_update.append("del" + i_id)
            self.keys_to_update.append(self['#ITEM_TYPE_LIST_2'][0])
        l = self['#ITEM_LIST']
        l.pop(l.index(i_id))
        self['#ITEM_LIST'] = l
        #del self[i_id]
        if sync:
            self.sync()
        
        return i_id

    
    def addPerson(self, data, sync = True):
        self['#PERS_COUNT'] += 1
        new_person = data
        new_person['ID'] = 'PERS#' + str(self['#PERS_COUNT'])
        new_person['rent_date'] = ""
        new_person['rent_old'] = []
        
        self[new_person['ID']] = new_person
        self.append('#PERS_LIST', new_person['ID'])
        if sync:
            self.sync()
        return new_person['ID']        

    def editPerson(self, data):
        self[data['ID']] = data
        self.sync()
        return data['ID']

    def deletePerson(self, p_id, sync = True):
        perss = self['#PERS_LIST']
        perss.pop(perss.index(p_id))
        self['#PERS_LIST'] = perss
        #del self[p_id]
        if sync:
            self.sync()        
        return p_id      

    def printPersons(self):
        print self['#PERS_COUNT']
        for p_id in self['#PERS_LIST']:
            print self[p_id]

    
    def regenerateWikiPages(self, widget = None):
        print "Rozpoczęto regenerację stron!"
        self["KEYS_TO_UPDATE"] = []
        tmp = []
        tmp.append(self['#ITEM_TYPE_LIST_2'][0])
        tmp.append("GROUP##" + self['#TEST_GROUP_LIST'][0])
        for i_id in self['#ITEM_LIST']:
            if not self[i_id]['test']:
                tmp.append(i_id)
        tmp += self['#TEST_LIST']
        self["KEYS_TO_UPDATE"] = tmp
        if widget:
            self.sync()


    def addTest(self, data):
        pprint.pprint(data)

        new_test = data
        if 'ID' in new_test.keys():
            print "\n\nedycja testu"
            # sprawdzić grupę
            old_test = self[new_test['ID']]
            if old_test['group'] != new_test['group']:
                print "zmiana grupy", old_test['group'], "na", new_test['group']
                l = self["GROUP##" + old_test['group']]
                print l, "-", new_test['ID']
                l.pop(l.index(new_test['ID']))
                self["GROUP##" + old_test['group']] = l
                print l
                # dodać do nowej
                if new_test['group'] not in self['#TEST_GROUP_LIST']:
                    self.append('#TEST_GROUP_LIST', new_test['group'], True)
                    self['GROUP##'+new_test['group']] = [new_test['ID']]
                else:
                    self.append('GROUP##'+new_test['group'], new_test['ID'])                
                # sprawdzić starą na warunek usunięcia
                if old_test['group'] != "Inne" and not len(l):
                    l = self['#TEST_GROUP_LIST']
                    l.pop(l.index(old_test['group']))
                    self['#TEST_GROUP_LIST'] = l
                    del self["GROUP##" + old_test['group']]

            # SYGNATURA !!!
            if len(old_test['items']) > 0:
                upper_sig = self[old_test['items'][-1]]['sig']
                sig, index = upper_sig.split("/")
                sig += "/"
                index = int(index)
            else:
                sig = new_test['ID'][5:] + "/"
                index = 0
            
            # zamienić dict na id, dodać do systemu, usunąć przedmioty których już nie ma
            new_ids = []
            deleted_items = []
            
            for i in new_test['items']:
                if 'ID' not in i.keys():                    
                    index += 1
                    new_item = i
                    new_item['sig'] = sig + str(index)
                    new_i_id = self.addTestItem(new_test['ID'], new_item)
                    new_ids.append(new_i_id)
                else:
                    self[i['ID']] = i
                    new_ids.append(i['ID'])
                    
            for i in old_test['items']:              
                if self[i]['ID'] not in new_ids:
                    print "usuwanie przedmiotu", i
                    deleted_items.append(self.deleteItem(i))
                    
            new_test['items'] = new_ids
    
            # wrzucić nowy słownik na miejsce starego
            self[new_test['ID']] = new_test
            pprint.pprint(self[new_test['ID']])
            #
            self.sync()
            return (new_test['ID'], deleted_items)
        
        new_test['ID'] = 'TEST#' + str(self['#TEST_COUNT'])

        i = 1
        tmp = []
        for item in data['items']:
            item['sig'] = str(self['#TEST_COUNT']) + "/" + str(i)
            iid = self.addTestItem(new_test['ID'], item)
            i +=1
            tmp.append(iid)
            
        new_test['items'] = tmp

        self[new_test['ID']] = new_test       
        self.append('#TEST_LIST', new_test['ID'])



        if data['group'] not in self['#TEST_GROUP_LIST']:
            self.append('#TEST_GROUP_LIST', data['group'], True)
            self['GROUP##'+data['group']] = [new_test['ID']]
        else:
            self.append('GROUP##'+data['group'], new_test['ID'])

        print "--" * 40, "TEST --"
        pprint.pprint(new_test)
        print "--" * 40, "TEST --"
        print self['#TEST_GROUP_LIST']
        
        self['#TEST_COUNT'] += 1
        self.sync()
        return new_test['ID']


    def printTests(self):
        for t_id in self['#TEST_LIST']:
            pprint.pprint(self[t_id])

    def addTestItem(self, test_id, data):
        
        new_item = data
        new_item['test'] = test_id
        new_item['ID'] = 'ITEM#' + str(self['#ITEM_COUNT'])
        self[new_item['ID']] = new_item
        self.append('#ITEM_LIST', new_item['ID'])
        self['#ITEM_COUNT'] += 1
        self.createItemHistory(new_item['ID'])
        return new_item['ID']
        

    def addItem(self, data):
        new_item = data
        new_item['test'] = ""
        new_item['ID'] = 'ITEM#' + str(self['#ITEM_COUNT'])
        new_item['sig'] = str(self['#ITEM_COUNT'])
        self[new_item['ID']] = new_item
        self.append('#ITEM_LIST', new_item['ID'])
        self['#ITEM_COUNT'] += 1
        self.createItemHistory(new_item['ID'])
        self.sync()
        return new_item['ID']

    def editItem(self, data):
        self[data['ID']] = data
        self.sync()
        return data['ID']

    def createItemHistory(self, iid):
        item = self[iid]
        if item['category'] in self.not_tracked_items:
            item['Q'] = 0
        else:
            item['Q'] = []
            item['last-sig'] = 0
            item['out'] = []

        item['history'] = []
        self[iid] = item

    def printItems(self):
        for i_id in self['#ITEM_LIST']:
            pprint.pprint(self[i_id])
