# coding: cp1250
# Rafal Jasicki
### archiwizacja.....

### TODO:
##
# łamanie długich linii w Labels (kasowanie, zasoby)
##
# prywatne info w opisie przedmiotu (okno ostateczne wypożyczania)
# lista dluznikow
# blokada usuniecia egzemplarza, potwierdzenie +
# przyciski czyszczenia +

import pygtk
pygtk.require('2.0')
import gtk, gobject
import string, Queue
#import wiki_thread, wiki_proxy
import dwthread as wiki_thread
import dwclient as wiki_proxy
import safedb
import tracker
import pprint
import time, datetime
from os import sep
import converter
import logging

logger = logging.getLogger("pracownia")


class MainWindow:
  
    def __init__(self, log_file = False):

        
        self.log_file = log_file

        self.gui_transitions = {
        'start': ['ready'],
        'ready': ['test-edit', 'test-new', 'item-edit', 'item-new', 'titem-edit', 'pers-new', 'pers-edit',
                  'pers-import', 'pers-his', 'test-his', 'item-his', 'rent-adv', 'dept-export'],
        'test-edit': ['ready', 'test-edit:titem-edit', 'test-edit:titem-new'],
        'test-new': ['ready', 'test-new:titem-edit', 'test-new:titem-new'],
        'item-new': ['ready'],
        'pers-new': ['ready'],
        'pers-edit': ['ready'],
        'pers-view': ['ready'],
        'pers-import': ['ready', 'pers-compare'],
        'pers-compare': ['ready'],
        'pers-his': ['ready'],
        'test-his': ['ready'],
        'item-his': ['ready'],
        'rent-adv': ['ready'],
        'dept-export': ['ready'],
        'END': []
            }
        self.tmp_dialog = [] # lista otwartych okien, ostatnie okno jest zawsze na wierzchu
        
        self.tracker = tracker.Tracker() # ostatnio utworzone obiekty, wpisane wartości itp
        self.tracker['current-test'] = None            # obecnie tworzony/edytowany
        self.tracker['current-test-item-ids'] = None   # dla widoku elementów należących do testu
        self.tracker['current-item'] = None            # obecnie tworzony/edytowany

        self.gui_state = 'start'

        # widoki:
        self.testStoreKeys = []
        self.itemStoreKeys = []
        self.shown_view = None  # None, lub lista z obiektami to ukrycia
        
        self.test_keys = []
        self.test_entries = []
        self.item_keys = []
        self.item_entries = []
        self.pers_keys = []
        self.pers_entries = []
        self.dummy_filtering = True
        
        self.config = None # safedb z konfiguracją programu i bazą danych
        self.config_state = False # wskazuje czy plik konfiguracyjny został odnaleziony

        self.mq = None # kolejka z wiadomościami od wikiProxy


        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        gobject.timeout_add(1000, self.getMessages)

        self.config = safedb.safedb()
        self.config.app = self
        self.feedback_queue = Queue.Queue()
        

        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)

        self.window.set_title("System biblioteczny")
        self.window.set_size_request(700, 600)
        
        self.tmp_dialog = [self.window]
        self.wiki_popup_open = False


        # glowny box pionowy
        self.main_box = gtk.VBox(False, 0)
        self.window.add(self.main_box)
        
        # ----------------------------------------------------------- Menu -
        #test = '''
        self.file_menu = gtk.Menu()
        file_item = gtk.MenuItem("Menu")
        menu_list = [("Generacja stron Wiki", self.regenerateWikiPages),
                     ("Lista dłużników", self.printDebtorListClicked),
                     ("Import kont studenckich", self.importPersonListClicked),
                     ("Zamknij", self.delete_event)]

        for item_pair in menu_list:
            item = gtk.MenuItem(item_pair[0].decode("cp1250").encode("UTF-8"))
            self.file_menu.append(item)
            item.connect ("activate", item_pair[1])
            item.show()        


        file_item.set_submenu(self.file_menu)

        self.menu_bar = gtk.MenuBar()
        self.menu_bar.append(file_item)
        file_item.show()

        self.file_menu.show()
        self.main_box.pack_start(self.menu_bar, False, False, 2)

        self.menu_bar.show()
        #'''
        # ------------------------------------------------------------------
        
        # -------------------- box z przyciskami polaczenia i konfiguracji -
        self.button_box = gtk.HBox(False, 0)
        self.bConfig = gtk.Button(" Konfiguracja ")
        self.bConfig.connect("clicked", self.openConfigPopUp)
        self.bWiki = gtk.Button("     Wiki     ")
        self.bWiki.connect("clicked", self.openWikiPopUp)

        self.c_image = gtk.Image()
        if self.config.tryFile("main.db"):
            self.c_image.set_from_file('gfx\\green.gif')
            self.config_state = True
        else:
            self.c_image.set_from_file('gfx\\red.gif')
            self.config_state = False
        self.c_image.show()
        self.w_image = gtk.Image()
        self.w_image.set_from_file('gfx\\yellow.gif')
        self.w_image.show()
        
        self.wiki = {}
        self.wiki['state'] = '???'
        

        if self.config_state:
            self.wikiLogin()
        else:
            self.w_image.set_from_file('gfx\\red.gif')
            self.wiki['state'] = 'Nie skonfigurowane.'

        self.main_box.pack_start(self.button_box, False, False, 2)
        self.button_box.pack_start(self.bConfig, False, False, 10)
        self.button_box.pack_start(self.c_image, False, False, 1)
        self.button_box.pack_start(self.bWiki, False, False, 10)
        self.button_box.pack_start(self.w_image, False, False, 1)

        self.bConfig.show()
        self.bWiki.show()

        self.button_box.show()
        # ------------------------------------------------------------------
        
        self.showButton()
        if self.config_state:
            self.readConfig()
        
        self.main_box.show()
        #'''
        self.window.show()


    def readConfig(self):
        self.showButton()
        self.testStoreCreation()
        self.shown_view = None
        self.showTests()
        self.itemStoreCreation()
        self.personStoreCreation()
        self.rentingCreation()
        self.rentingFinishCreation()
        self.show_buttons.show()
        self.gui_state = 'ready'
        
        
    
    def computeAvailability(self, test):
        if len(test['items']) == 0:
            return 0
        tmp = 100
        for i in test['items']:
            value = self.computeItemAvailability(i)
            if value < tmp:
                tmp = value
        return tmp

    def showButton(self):
        self.show_buttons = gtk.HBox(False, 0)
        modes = [(" Testy ", self.showTests), (" Przedmioty ", self.showItems), (" Konta wypożyczających ", self.showPersons),
                 (" Wypożyczanie ", self.showRenting)]
        
        group = None
        for m in modes:
            button = gtk.RadioButton(group, m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            group = button.get_group()[0]
            button.show()
            self.show_buttons.pack_start(button, False, False, 2)
            
        self.main_box.pack_start(self.show_buttons, False, False, 2)
        hseparator = gtk.HSeparator()
        hseparator.show()
        self.main_box.pack_start(hseparator, False, False, 2)



    def hideShown(self):
        #return
        if self.shown_view:
            for w in self.shown_view:
                w.hide()
        if not self.dummy_filtering:
            self.clearPersonChoosingFields()
            self.clearItemChoosingFields()
            self.dummy_filtering = True
        self.shown_view = None

    def showTests(self, widget = None):
        self.hideShown()
        for w in self.test_view_list:
            w.show()
        self.shown_view = self.test_view_list

    def showItems(self, widget = None):
        self.hideShown()
        for w in self.item_view_list:
            w.show()
        self.shown_view = self.item_view_list
        
    def showPersons(self, widget = None):
        self.hideShown()
        for w in self.person_view_list:
            w.show()
        self.shown_view = self.person_view_list

    def showRenting(self, widget = None):
        self.hideShown()
        for w in self.renting_view_list:
            w.show()
        self.shown_view = self.renting_view_list
        self.dummy_filtering = False

    def showRentingFinish(self, widget = None):
        for w in self.shown_view:
            w.hide()
        for w in self.renting_finalization_view_list:
            w.show()
        self.shown_view = self.renting_finalization_view_list
 

    #========================================================================================================
    #                               TEST VIEW
    #========================================================================================================
    def createTestRow(self, t_id):
        keys = self.testStoreKeys
        test = self.config[t_id]
        tmp = []
        for k in keys:
            tmp.append(test[k])
        tmp.append(self.computeAvailability(test))

        tmp[1] = int(tmp[1].split('#')[1])
        
        return tmp     

    def testStoreCreation(self):
        keys  = ['ID', 'ID',    'group', 'test:name', 'author', 'publisher']# 'availability']
        names = ['ID', 'N.', 'Grupa', 'Nazwa',     'Autor',  'Wydawnictwo']# 'availability']

        self.testStoreKeys = keys
        
        self.test_store = gtk.ListStore(str, int, str, str, str, str, int)
        for t_id in self.config['#TEST_LIST']:
            self.test_store.append(self.createTestRow(t_id))           
    
        self.test_view = gtk.TreeView(self.test_store)
        #self.text_cell_renderer = gtk.CellRendererText()
        self.text_cell_renderer = gtk.CellRendererText()
        self.text_cell_renderer.set_property("wrap-width", 200)
        #self.text_cell_renderer_short = gtk.CellRendererText()
        #self.text_cell_renderer_short.set_property("wrap-width", 50)
        
        for i in range(1, len(keys)):
            column = gtk.TreeViewColumn(names[i].decode("cp1250").encode("UTF-8"))
            self.test_view.append_column(column)
            column.pack_start(self.text_cell_renderer, True)
            column.add_attribute(self.text_cell_renderer, 'text', i)            
            column.set_sort_column_id(i)
            column.set_resizable(True)

        column = gtk.TreeViewColumn("Dostępność".decode("cp1250").encode("UTF-8"))

        self.test_view.append_column(column)
        self.bar_cell_renderer = gtk.CellRendererProgress()
        column.pack_start(self.bar_cell_renderer, True)
        column.add_attribute(self.bar_cell_renderer, 'value', len(keys))
        column.set_sort_column_id(len(keys))

        self.test_scrolled_window = gtk.ScrolledWindow()
        self.test_scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.test_scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.test_scrolled_window.add(self.test_view)
        
        self.test_view.show()        

        box = gtk.HBox(False, 0)

        modes = [(" Stwórz test ", self.openNewTestDialogPopUp), (" Edytuj test ", self.openEditTestDialogPopUp),
                 # -- bo tak! (" Historia ", self.printTestHistoryClicked),
                 (" Zasoby ", self.testResourcesClicked), (" Usuń test ", self.deleteTestClicked, 50)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            if len(m) > 2:
                box.pack_start(button, False, False, m[2])
            else:
                box.pack_start(button, False, False, 2)
            
        self.main_box.pack_start(box, False, False, 2)
        self.main_box.pack_start(self.test_scrolled_window, True, True, 2)

        self.test_view_list = [self.test_scrolled_window, box]

    #========================================================================================================
    #                               PERSON VIEW
    #========================================================================================================
    def createPersonRow(self, p_id):
        keys = self.personStoreKeys
        person = self.config[p_id]
        tmp = []
        for k in keys[:-2]:
            try:
                tmp.append(person[k])
            except:
                tmp.append('---')
        tmp.append(len(person['rent']))
        tmp.append(person[keys[-1]])
        
        return tmp

    def personStoreCreation(self):
        keys  = ['ID', 'pers:name', 'pers:lname', 'year', 'indx'       , 'count',        'rent_date']
        names = ['ID', 'Imię',      'Nazwisko',   'Rok',  'Indeks/inne', 'Wypożyczenia', 'Termin']

        self.personStoreKeys = keys
          
        self.person_store = gtk.ListStore(str, str, str, str, str, int, str)
        for p_id in self.config['#PERS_LIST']:
            self.person_store.append(self.createPersonRow(p_id))            

        self.person_view = gtk.TreeView(self.person_store)
        
        for i in range(1, len(keys)):
            column = gtk.TreeViewColumn(names[i].decode("cp1250").encode("UTF-8"))
            self.person_view.append_column(column)
            column.pack_start(self.text_cell_renderer, True)
            column.add_attribute(self.text_cell_renderer, 'text', i)            
            column.set_sort_column_id(i)
            column.set_resizable(True)

  
        self.person_scrolled_window = gtk.ScrolledWindow()
        self.person_scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.person_scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.person_scrolled_window.add(self.person_view)

        self.person_view.show()


        box = gtk.HBox(False, 0)

        modes = [
                 (" Dodaj nowe konto studenckie ", self.openNewPersonDialogPopUp), (" Dodaj nowe konto ", self.openOuterNewPersonDialogPopUp),
                 (" Edytuj konto ", self.openEditPersonDialogPopUp), 
                 (" Historia ", self.printPersonHistoryClicked),
                 (" Usuń konto ", self.deletePersonClicked, 50)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            if len(m) > 2:
                box.pack_start(button, False, False, m[2])
            else:
                box.pack_start(button, False, False, 2)
            
        self.main_box.pack_start(box, False, False, 2)
        self.main_box.pack_start(self.person_scrolled_window, True, True, 2)

        self.person_view_list = [self.person_scrolled_window, box]


    
    #========================================================================================================
    #                               ITEM VIEW
    #========================================================================================================
    def createItemRow(self, i_id):
        item = self.config[i_id]
        keys = self.itemStoreKeys        
        tmp = []
        for k in keys:
            tmp.append(item[k])
        if len(tmp[1]) > 0:
            tmp[1] = self.config[tmp[1]]['test:name']
        tmp.append(self.computeItemAvailability(i_id))
        if isinstance(item['Q'], int):
            tmp.append(item['Q'])# - item['out'])
        else:
            tmp.append(len(item['Q']) - len(item['out']))
        
        return tmp

    
    def computeItemAvailability(self, i_id):
        i = self.config[i_id]
        if i['desired'] == 0:
            return 100            
        if isinstance(i['Q'], int):
            return int(min(  [ 100, 100.0 * i['Q'] / i['desired']]  ))
        else:
            return int(min(  [ 100, 100.0 * (len(i['Q']) - len(i['out'])) / i['desired']]  ))               


    def itemStoreCreation(self):
        keys  = ['ID', 'test', 'item:name', 'author', 'publisher', 'category',  'sig']# 'availability', 'on hand']
        names = ['ID', 'Test', 'Nazwa',     'Autor',  'Wydawca',   'Kategoria', '(sygnatura)']# 'availability', 'on hand']

        self.itemStoreKeys = keys
          
        self.item_store = gtk.ListStore(str, str, str, str, str, str, str, int, int)
        for i_id in self.config['#ITEM_LIST']:
            self.item_store.append(self.createItemRow(i_id))            
        
        self.item_view = gtk.TreeView(self.item_store)
        
        for i in range(1, len(keys)):
            column = gtk.TreeViewColumn(names[i].decode("cp1250").encode("UTF-8"))
            self.item_view.append_column(column)
            column.pack_start(self.text_cell_renderer, True)
            column.add_attribute(self.text_cell_renderer, 'text', i)            
            column.set_sort_column_id(i)
            column.set_resizable(True)

        column = gtk.TreeViewColumn("Dostępność".decode("cp1250").encode("UTF-8"))

        self.item_view.append_column(column)
        column.pack_start(self.bar_cell_renderer, True)
        column.add_attribute(self.bar_cell_renderer, 'value', len(keys))
        column.set_sort_column_id(len(keys))
  
        self.item_scrolled_window = gtk.ScrolledWindow()
        self.item_scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.item_scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.item_scrolled_window.add(self.item_view)

        self.item_view.show()


        box = gtk.HBox(False, 0)

        modes = [(" Stwórz osobny przedmiot ", self.createItemButton), (" Edytuj przedmiot ", self.editItemButton),
                 (" Historia ", self.printItemHistoryClicked),
                 (" Zasoby ", self.itemResourcesClicked), (" Usuń przedmiot ", self.deleteItemClicked, 50)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            if len(m) > 2:
                box.pack_start(button, False, False, m[2])
            else:
                box.pack_start(button, False, False, 2)
            
        self.main_box.pack_start(box, False, False, 2)
        self.main_box.pack_start(self.item_scrolled_window, True, True, 2)

        self.item_view_list = [self.item_scrolled_window, box]
        
    #========================================================================================================
    #                               RENTING VIEW
    #========================================================================================================

      

    def rentingCreation(self):
        self.chosen_rent_person = None
        self.renting_view_list = []
        modes = [('person', "Wybierz osobę"),('item', "Wybierz przedmioty")]
        for mode in modes:
            frame = gtk.Frame(mode[1].decode("cp1250").encode("UTF-8"))
            box = gtk.HBox(True, 0)
            box.set_homogeneous(False)
          
            if mode[0] == 'person':
                vbox = gtk.VBox(False, 0)
                vbox.set_homogeneous(False)

                controls = [("Imię:                     ","pers:name", 1),
                            ("Nazwisko:               ","pers:lname", 2),
                            ("Indeks/inne:           ", "indx", 4)]
                textfields = []

                person_filter = self.person_store.filter_new()
                view = gtk.TreeView(person_filter)
                
               
                for c in controls:
                    label = gtk.Label(c[0].decode("cp1250").encode("UTF-8"))
                    vbox.pack_start(label, False, False, 2)
                    field = gtk.Entry()
                    field.set_editable(True)
                    field.connect("changed", self.personChoosing)
                    vbox.pack_start(field, False, True, 2)

                    label.show()
                    field.show()
                    textfields.append([field, c[1], c[2], ""])

                    column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
                    view.append_column(column)
                    column.pack_start(self.text_cell_renderer, True)
                    column.add_attribute(self.text_cell_renderer, 'text', c[2])
                    column.set_sort_column_id(c[2])
                    column.set_resizable(True)

                button = gtk.Button(" Wyczyść ".decode("cp1250").encode("UTF-8"))
                button.connect("clicked", self.clearPersonChoosingFields)
                button.show()
                vbox.pack_start(button, False, False, 10)
                view.connect("cursor-changed", self.displayPersonData)

                self.personChoosingFields = textfields
                person_filter.set_visible_func(personVisibility, self)
                self.person_filter = person_filter
                self.person_filter_view = view
                
                vbox.show()
                box.pack_start(vbox, False, False, 2)
                window = gtk.ScrolledWindow()
                window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                window.set_shadow_type(gtk.SHADOW_IN)
                window.add(view)
                window.show()
                view.show()
                box.pack_start(window, True, True, 2)

                vbox = gtk.VBox(False, 0)

                label = gtk.Label(self.person2string())
                vbox.pack_start(label, False, False, 2) 
                label.show()
                self.personDataLabel = label

                button = gtk.Button(" Wyświetl wypożyczone ".decode("cp1250").encode("UTF-8"))
                button.connect("clicked", self.openAdvancedRent)
                button.show()
                vbox.pack_start(button, False, False, 10)
                vbox.show()
                box.pack_start(vbox, False, False, 2)



            else:
                # kontrolki dla wyboru testu
                searchbox = gtk.VBox(False, 0)
                #label = gtk.Label("aaa")
                #searchbox.pack_start(label, False, False, 2)
                #label.show()
                ####
                controls = [("Test:                     ","test", 1),
                            ("Nazwa:                    ","item:name", 2),
                            ("Sygnatura:                ","sig", 6)]

                textfields = []
##
                item_filter = self.item_store.filter_new()
                view = gtk.TreeView(item_filter)
##                
##               
                for c in controls:
                    label = gtk.Label(c[0].decode("cp1250").encode("UTF-8"))
                    searchbox.pack_start(label, False, False, 2)
                    field = gtk.Entry()
                    field.set_editable(True)
                    field.connect("changed", self.itemChoosing)
                    searchbox.pack_start(field, False, True, 2)
##
                    label.show()
                    field.show()
                    textfields.append([field, c[1], c[2], ""])
##
                    column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
                    view.append_column(column)
                    column.pack_start(self.text_cell_renderer, True)
                    column.add_attribute(self.text_cell_renderer, 'text', c[2])
                    column.set_sort_column_id(c[2])
                    column.set_resizable(True)

                column = gtk.TreeViewColumn("Dostępne".decode("cp1250").encode("UTF-8"))
                view.append_column(column)
                column.pack_start(self.text_cell_renderer, True)
                column.add_attribute(self.text_cell_renderer, 'text', 8)
                column.set_sort_column_id(8)
                column.set_resizable(True)                    
##
                button = gtk.Button(" Wyczyść ".decode("cp1250").encode("UTF-8"))
                button.connect("clicked", self.clearItemChoosingFields)
                button.show()
                searchbox.pack_start(button, False, False, 10)

                ####
                box.pack_start(searchbox, False, False, 2)
                searchbox.show()
                
                self.itemChoosingFields = textfields
                item_filter.set_visible_func(itemVisibility, self)
                self.item_filter = item_filter
                self.item_filter_view = view
                
               
                #view = gtk.TreeView(self.item_store)
                #view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
                #columns = [("Test", 1), ("Nazwa", 2), ("Dostępne", 8)]
                #for c in columns:
                #    column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
                #    view.append_column(column)
                #    column.pack_start(self.text_cell_renderer, True)
                #    column.add_attribute(self.text_cell_renderer, 'text', c[1])
                #    column.set_sort_column_id(c[1])
                #    column.set_resizable(True)


                window = gtk.ScrolledWindow()
                window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                window.set_shadow_type(gtk.SHADOW_IN)
                window.add(view)
                window.show()
                view.show()
                self.rentFromView = view
                box.pack_start(window, True, True, 2)
                
                vbox = gtk.VBox(True, 0)
                for m in [(" Dodaj -> ", self.addItemToRentList), (" <- Usuń ", self.removeItemFromRentList),
                          (" Wypożycz ", self.rentingFinish)]:
                    button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
                    button.connect("clicked", m[1])
                    button.show()
                    vbox.pack_start(button, False, False, 2)
                    
                vbox.show()
                box.pack_start(vbox, False, False, 2)

                self.rent_list = gtk.ListStore(str, str, str, str, str, str, str, int, int)
                view = gtk.TreeView(self.rent_list)
                view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
                columns = [("Test", 1), ("Nazwa", 2)]
                for c in columns:
                    column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
                    view.append_column(column)
                    column.pack_start(self.text_cell_renderer, True)
                    column.add_attribute(self.text_cell_renderer, 'text', c[1])
                    column.set_sort_column_id(c[1])
                    column.set_resizable(True)

                window = gtk.ScrolledWindow()
                window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                window.set_shadow_type(gtk.SHADOW_IN)
                window.add(view)
                window.show()
                self.rentView = view
                view.show()
                box.pack_start(window, True, True, 2)
                
            box.show()
            frame.add(box)
            self.tracker['chosen-rent-items'] = []

            self.renting_view_list.append(frame)
            self.main_box.pack_start(frame, True, True, 2)

            self.dummy_filter = False
            


    def rentingFinish(self, widget = None):
        if self.chosen_rent_person == None:
            return
        if len(self.rent_list) == 0:
            return
        self.descriptionField.get_buffer().set_text(self.item2string())
        self.showRentingFinish()
        
        for item_row in self.rent_list:
            i_id = item_row[0]
            item = self.config[i_id]
            desc1 = self.item2string(item['ID'])
            if item['category'] not in self.config.not_tracked_items:
                
                for sig in item['Q']:
                    if len(sig) == 2:
                        self.sig_list.append([sig[0], desc1 + sig[0] + " : " + sig[1], False, 7])
            else:
                # zamienić
                self.sig_list.append([item['sig'] + item['category'][5:], desc1 + item['category'][6:], True, 10])
                        
        # umieścić przedmioty z syg. na liście


    def toggleAction(self, widget, inx):
        self.sig_list[inx][2] = not self.sig_list[inx][2]

    def spinnerAction(self, widget, inx, value):

        (model, ite) = self.rentedView.get_selection().get_selected()
        if ite == None:
            self.descriptionField.get_buffer().set_text(self.item2string())
            return
        
        logger.info(model[ite][0])
        for row in self.sig_list:
            if row[0] == model[ite][0]:
                row[3] = int(value)
                return

    def rentingFinishCreation(self, widget = None):

        self.renting_finalization_view_list = []
        box = gtk.HBox(True, 0)
        box.set_homogeneous(False)

        self.toggle_cell_renderer = gtk.CellRendererToggle()
        #self.toggle_cell_renderer.set_property("editable", True)
        self.toggle_cell_renderer.set_property('activatable', True)
        self.toggle_cell_renderer.connect("toggled", self.toggleAction)#, (model, column))

        
        self.sig_list = gtk.ListStore(str, str, bool, int)
        view = gtk.TreeView(self.sig_list)
        view.get_selection().set_mode(gtk.SELECTION_BROWSE)
        columns = [("Sygnatura", 0), ("Dodaj", 2)]
        for c in columns:
            column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
            view.append_column(column)
            if c[1] == 0:
                column.pack_start(self.text_cell_renderer, True)
                column.add_attribute(self.text_cell_renderer, 'text', c[1])
                column.set_sort_column_id(c[1])
            else:
                column.pack_start(self.toggle_cell_renderer, True)
                column.add_attribute(self.toggle_cell_renderer, "active", c[1])
                
                
            column.set_resizable(True)
        view.connect("cursor-changed", self.displayItemData)
        window = gtk.ScrolledWindow()
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.add(view)
        window.show()
        self.rentFinishView = view
        view.show()
        box.pack_start(window, True, True, 2)

        window = gtk.ScrolledWindow()
        self.descriptionField = gtk.TextView()
        self.descriptionField.set_editable(False)
        self.descriptionField.get_buffer().set_text(self.item2string())    
        self.descriptionField.set_wrap_mode(gtk.WRAP_WORD)
        window.add(self.descriptionField) 
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.show()
            
        self.descriptionField.show()
        box.pack_start(window, True, True, 2)
        hbox = gtk.HBox(True, 2)
        hbox.set_homogeneous(False)

        sig_filter = self.sig_list.filter_new()
        view = gtk.TreeView(sig_filter)
        sig_filter.set_visible_column(2)


        self.spin_cell_renderer = gtk.CellRendererSpin()
        self.spin_cell_renderer.set_property("editable", True)
        adj = gtk.Adjustment(0, 0, 1000, 1, 7)
        self.spin_cell_renderer.set_property("adjustment", adj)
        self.spin_cell_renderer.connect("edited", self.spinnerAction)


        columns = [("Sygnatura", 0), ("Dni/ilość", 3)]
        for c in columns:
            column = gtk.TreeViewColumn(c[0].decode("cp1250").encode("UTF-8"))
            view.append_column(column)
            if c[1] == 0:
                column.pack_start(self.text_cell_renderer, True)
                column.add_attribute(self.text_cell_renderer, 'text', c[1])
                column.set_sort_column_id(c[1])
            else:
                column.pack_start(self.spin_cell_renderer, True)
                column.add_attribute(self.spin_cell_renderer, "text", c[1])
            column.set_resizable(True)

        view.connect("cursor-changed", self.displayItemData2)
        window = gtk.ScrolledWindow()
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.add(view)
        window.show()
        self.rentedView = view
        view.show()
        vbox = gtk.VBox(True, 2)
        vbox.set_homogeneous(False)
        vbox.pack_start(window, True, True, 2)
        vbox.show()
        buttonBox = gtk.HBox(True, 2)
        buttons = [(" Cofnij ", self.abandonRent),(" Wykonaj ", self.applyRenting)]
        for e in buttons:
            b = gtk.Button(e[0].decode("cp1250").encode("UTF-8"))
            b.connect("clicked", e[1])
            buttonBox.pack_start(b, False, False, 2)
            b.show()
        
        buttonBox.show()
        vbox.pack_start(buttonBox, False, False, 2)
        box.pack_start(vbox, True, True, 0)
        

        self.renting_finalization_view_list.append(box)
        self.main_box.pack_start(box, True, True, 2)

    def abandonRent(self, widget = None):
        for i in range(len(self.sig_list)):
            del self.sig_list[-1]
        self.showRenting()
        

    def time2string(self, time_v):
        data = time.localtime(time_v)
        return ".".join([str(data[0]), str(data[1]).zfill(2), str(data[2]).zfill(2)])

    def applyRenting(self, widget = None):
        logger.info("Apply renting")
        now = time.time()
        day = 24 * 60 * 60
        data_str = self.time2string(now)
        #print data, self.chosen_rent_person
        person = self.config[self.chosen_rent_person]
        if person['rent_date'] == "":
            first_date = "9999"
        else:
            first_date = person['rent_date']

        items_to_update = []
        tests_to_update = []
        
        for e in self.sig_list:
            
            rented = []
            if e[2]:
                logger.info((e[0], e[3]))
                sig = e[0].split()
                if len(sig) > 1:
                    sig[0] += "/0"

                sig = sig[0].split("/")
                if len(sig) > 2:
                    logger.info("test item")
                    t_id = "TEST#" + sig[0]
                    tests_to_update.append(t_id)
                    item_sig = sig[0] + "/" + sig[1]
                    logger.info(t_id)
                    test = self.config[t_id]
                    for i_id in self.config[t_id]['items']:
                        if self.config[i_id]['sig'] == item_sig:
                            item = self.config[i_id]
                            if item['category'] in self.config.not_tracked_items:
                                item['Q'] -= e[3]
                                item['history'].append([item['sig'], 'wypożyczone w liczbie '.decode("cp1250").encode("UTF-8") + str(e[3]),
                                                       data_str, person['ID']])
                                person['rent_old'].append([i_id, 'pobrane', data_str, e[3]])                                

                            else:
                                data_e = self.time2string(now + (int(e[3]) * day))
                                item_sig = item_sig + "/" + sig[2]
                                item['out'].append([item_sig, data_str, data_e, person['ID']])
                                item['history'].append([item_sig, 'wypożyczone'.decode("cp1250").encode("UTF-8"), data_str, person['ID']])
                                person['rent_old'].append([i_id, 'wypożyczone'.decode("cp1250").encode("UTF-8"), data_str, item_sig])
                                person['rent'].append([i_id, 'do zwrotu'.decode("cp1250").encode("UTF-8"), data_e, item_sig])
                                for inx in range(len(item['Q'])):
                                    if item_sig == item['Q'][inx][0]:
                                        logger.info(item['Q'][inx])
                                        item['Q'][inx] += [data_str, data_e, person['ID']]
                                        
                                if data_e < first_date:
                                    first_date = data_e
                            
                            self.config[i_id] = item
                            items_to_update.append(i_id)
                else:
                    logger.info("other item")
                    i_id = "ITEM#" + sig[0]
                    logger.info(i_id)
                    items_to_update.append(i_id)
                    data_e = self.time2string(now + (int(e[3]) * day))
                    item_sig = sig[0] + "/" + sig[1]
                    item = self.config[i_id]
                    item['out'].append([item_sig, data_str, data_e, person['ID']])
                    item['history'].append([item_sig, 'wypożyczone'.decode("cp1250").encode("UTF-8"), data_str, person['ID']])
                    person['rent_old'].append([i_id, 'wypożyczone'.decode("cp1250").encode("UTF-8"), data_str, item_sig])
                    person['rent'].append([i_id, 'do zwrotu'.decode("cp1250").encode("UTF-8"), data_e, item_sig])
                    for inx in range(len(item['Q'])):
                        if item_sig == item['Q'][inx][0]:
                            logger.info(item['Q'][inx])
                            item['Q'][inx] += [data_str, data_e, person['ID']]
                    if data_e < first_date:
                        first_date = data_e

                    self.config[i_id] = item
        
        
        if first_date != "9999":
            person['rent_date'] = first_date

        logger.info(person['rent'])
        logger.info(person['rent_old'])
        self.config[person['ID']] = person
        self.config.sync()
        self.updatePersonRow(person['ID'])
        for i_id in items_to_update:
            self.updateItemRow(i_id)
        for t_id in tests_to_update:
            self.updateTestRow(t_id)            
        self.abandonRent()
    

    def displayItemData(self, widget = None):
        (model, ite) = self.rentFinishView.get_selection().get_selected()
        if ite == None:
            self.descriptionField.get_buffer().set_text(self.item2string())
            return
        self.descriptionField.get_buffer().set_text(model.get_value(ite, 1))
        
    def displayItemData2(self, widget = None):
        (model, ite) = self.rentFinishView.get_selection().get_selected()
        if ite == None:
            self.descriptionField.get_buffer().set_text(self.item2string())  
            return
        self.descriptionField.get_buffer().set_text(model.get_value(ite, 1))

    def item2string(self, i_id = None):
        if i_id == None:
            return 'Test:\n\n\nPrzedmiot:\n\n\nEgzemplarz:'
        item = self.config[i_id]
        if item['test'] != "":
            test = self.config[item['test']]
            test_name = test['test:name'] + "\n" + test['test:private']
        else:
            test_name = ""
        txt_l = ['Test: ', test_name, '\nPrzedmiot: ', item['item:name'], "\n", item['item:private'],
                 '\nEgzemplarz: ']
        return "".join(txt_l)
        
        
        

    def addItemToRentList(self, widget = None):
        (model, ites) = self.rentFromView.get_selection().get_selected_rows()
        if ites == None:
            return

        logger.info((model, self.item_store))

        for ite in ites:
            if model[ite][0] not in self.tracker['chosen-rent-items']:
                self.tracker['chosen-rent-items'].append(model[ite][0])
                self.rent_list.append(model[ite])

    def removeItemFromRentList(self, widget = None):
        (model, ites) = self.rentView.get_selection().get_selected_rows()
        if ites == None:
            return
        ites.reverse()
        for ite in ites:
            self.tracker['chosen-rent-items'].pop(self.tracker['chosen-rent-items'].index(self.rent_list[ite][0]))
            del self.rent_list[ite]

    def displayPersonData(self, widget = None):
        (model, ite) = self.person_filter_view.get_selection().get_selected()
        if ite == None:
            self.personDataLabel.set_text(self.person2string())
            self.chosen_rent_person = None
            return
        self.personDataLabel.set_text(self.person2string(model.get_value(ite, 0)))
        self.chosen_rent_person = model.get_value(ite, 0)

    def person2string(self, p_id = None):
        if p_id == None:
            return "Imię:\nNazwisko:\nIndeks/inne:\nWypożyczonych:\n".decode("cp1250").encode("UTF-8") + " " * 80
        p = self.config[p_id]
        s = "Imię: ".decode("cp1250").encode("UTF-8") + p['pers:name'] + \
        "\nNazwisko: ".decode("cp1250").encode("UTF-8") + p['pers:lname'] + \
        "\nIndeks/inne: ".decode("cp1250").encode("UTF-8") + p['indx'] + \
        "\nWypożyczonych: ".decode("cp1250").encode("UTF-8") + str(len(p['rent'])) + "\n" + " " * 80
        return s
            

    def personChoosing(self, widget):
        if self.dummy_filter:
            return
        for i in range(len(self.personChoosingFields)):
            if self.personChoosingFields[i][0] == widget:
                logger.info("Edytowane pole numer: {}".format(str(i)))
                self.personChoosingFields[i][3] = widget.get_text()
                self.person_filter.refilter()
                self.displayPersonData()
                return

    def clearPersonChoosingFields(self, widget = None):
        for i in range(len(self.tracker['chosen-rent-items'])):
            del self.rent_list[0]
        self.tracker['chosen-rent-items'] = []
        self.dummy_filtering = True
        for i in range(len(self.personChoosingFields)):
            self.personChoosingFields[i][3] = ""
            self.personChoosingFields[i][0].set_text("")

        self.person_filter.refilter()
        self.dummy_filtering = False
        for i in range(len(self.sig_list)):
            del self.sig_list[-1]
            
    def itemChoosing(self, widget):
        if self.dummy_filter:
            return
        for i in range(len(self.itemChoosingFields)):
            if self.itemChoosingFields[i][0] == widget:
                print "Edytowane pole numer:", i
                self.itemChoosingFields[i][3] = widget.get_text()
                self.item_filter.refilter()
                return


    def clearItemChoosingFields(self, widget = None):
        #for i in range(len(self.tracker['chosen-rent-items'])):
        #    del self.rent_list[0]
        #self.tracker['chosen-rent-items'] = []
        self.dummy_filtering = True
        for i in range(len(self.itemChoosingFields)):
            self.itemChoosingFields[i][3] = ""
            self.itemChoosingFields[i][0].set_text("")
        self.item_filter.refilter()
        self.dummy_filtering = False

    #========================================================================================================
    #                               ADVANCED RENT WINDOW
    #========================================================================================================


    def openAdvancedRent(self, widget = None):
        """
        Przycisk "Zobacz wypożyczone" w widoku wypożyczeń
        """
        if not self.chosen_rent_person:
            return
        if not self.check_gui_transition('rent-adv'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'rent-adv'"
            return
        self.gui_state = 'rent-adv'

        #self.tracker['current-pers'] = {'rent': []}

        #d_title = "Tworzenie nowego konta".decode("cp1250").encode("UTF-8")

        self.advancedRentDialogPopUp(None, self.chosen_rent_person)

    def changeRentTimeAction(self, widget, inx, value):
        # 1. pobrać nową wartość, zamienić ją na datę 
        # 2. zmienić wartość w tracker'current-pers' 
        # 3. zmienić wartość w current store 
        # 4. zmienić wartośc w przedmiocie 
        # 5. zmienić "rent_date" 
        print "zmiana czasu wypożyczenia:", inx, value
        self.currentstore[inx][5] = int(value)
        value = int(value)
        value *= 60*60*24
        new_date = self.time2string(time.time()+value)
        print "new date:", new_date
        self.currentstore[inx][4] = new_date

        self.tracker['current-pers']['rent'][int(inx)][2] = new_date
        element = self.tracker['current-pers']['rent'][int(inx)]
        rent_date = new_date
        for rented in self.tracker['current-pers']['rent']:
            if rented[2] < rent_date:
                rent_date = rented[2]
                
        if self.tracker['current-pers']['rent_date'] != rent_date:
            print "change:", self.tracker['current-pers']['rent_date'], rent_date
            self.tracker['current-pers']['rent_date'] = rent_date
        print element

        i_id = element[0]
        sig = element[3]

        
        item = self.config[i_id]
        for i in range(len(item['out'])):
            element = item['out'][i]
            if element[0] == sig:
                item['out'][i][2] = new_date

        for i in range(len(item['Q'])):
            element = item['Q'][i]
            if element[0] == sig:
                item['Q'][i][3] = new_date
                
        self.config[i_id] = item

        p_dict = self.tracker['current-pers']
        self.config[p_dict['ID']] = p_dict
        self.config.sync()
        self.updatePersonRow(p_dict['ID'])


    def advancedRentDialogPopUp(self, widget = None, p_id = None):
        """
        Okno edycji wypożyczonych przedmiotów
        """

        p_dict = self.config[p_id]
        self.tracker['current-pers'] = p_dict
        
        dialog = gtk.Dialog(title="Konto: " + p_dict['pers:name'] + " " + p_dict['pers:lname'], parent=self.window, 
                            flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        
        dialog.set_size_request(550, 450)

        window = gtk.ScrolledWindow()
        self.currentstore = gtk.ListStore(str, str, str, str, str, int) # ???

        ###
        # co trzeba:
        # 1. dodać kontrolkę przesuwania dni...
        # 3. przeszmuglować automatyczną aktualizację
        # 4. zrobić aktualizację wyświetlanego info o wypożyczającym

        self.spin_cell_renderer_change = gtk.CellRendererSpin()
        self.spin_cell_renderer_change.set_property("editable", True)
        adj = gtk.Adjustment(0, 0, 1000, 1, 7)
        self.spin_cell_renderer_change.set_property("adjustment", adj)
        self.spin_cell_renderer_change.connect("edited", self.changeRentTimeAction)
        
        view_names = ["ID", "test", "nazwa", "syg", "Termin oddania", "Pozostało dni"]
        #view_indx  = [      0,       3,     1 ]    
        
####
        for r in self.tracker['current-pers']['rent']:
            #for k in view_keys:
            #    tmp.append(str(i[k]))
            item = self.config[r[0]]
            if item['test'] != "":
                test = self.config[item['test']]['test:name']
            else:
                test = ""
            end_date = map(lambda x: int(x), r[2].split("."))
            now = map(lambda x: int(x), self.time2string(time.time()).split("."))
            left_time = datetime.date(*end_date) - datetime.date(*now)
            print "left_time:", left_time
            self.currentstore.append([r[0], test, self.config[r[0]]['item:name'], r[3], r[2], left_time.days])
        
        treeview = gtk.TreeView(self.currentstore)
        for i in range(1, len(view_names)):
            tvcolumn = gtk.TreeViewColumn(view_names[i].decode("cp1250").encode("UTF-8"))
            treeview.append_column(tvcolumn)
            if i != len(view_names)-1:
                cell = gtk.CellRendererText()
                tvcolumn.pack_start(cell, True) # True = expand
                tvcolumn.add_attribute(cell, 'text', i)
            else:
                tvcolumn.pack_start(self.spin_cell_renderer_change, True)
                tvcolumn.add_attribute(self.spin_cell_renderer_change, "text", i)
            
            tvcolumn.set_sort_column_id(i)

        frame = gtk.Frame("Wypożyczone przedmioty:".decode("cp1250").encode("UTF-8"))
        window.add(treeview)
        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.currentview = treeview
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.show()
        frame.add(window)
        frame.show()

        dialog.vbox.pack_start(frame, True, True, 2)
        treeview.show()
####
        modes = [(" Zwrot ", self.returnItem), (" Zakończ ", self.applyRentTimeChange)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            dialog.action_area.pack_start(button, True, True, 3)

        dialog.show()

    def applyRentTimeChange(self, widget = None):
                 
        self.abort()


    #========================================================================================================
    #                               GUI STATE LOGIC
    #========================================================================================================

    def check_gui_transition(self, new_gui_state):
        print "\n  *** Poprzedni stan:", self.gui_state, "proponowany:", new_gui_state
        print
        return new_gui_state in self.gui_transitions[self.gui_state]
      
    def destroy_tmp(self, widget = None, data = None):        
        if len(self.tmp_dialog) > 1:
            self.tmp_dialog[-2].set_modal(True)
            self.tmp_dialog.pop().destroy()
            if len(self.tmp_dialog) == 1:
                self.tmp_dialog[0].set_modal(False)
        self.wiki_popup_open = False

    def abort(self, widget = None, data = None):
        if self.gui_state in ['test-edit', 'test-new']:
            self.gui_state = 'ready'
            self.test_keys = []
            self.test_entries = []
            self.tracker['current-test'] = None
            self.tracker['current-test-item-ids'] = None
        
        elif self.gui_state in ['test-edit:titem-edit', 'test-edit:titem-new']:
            self.gui_state = 'test-edit'
            self.item_keys = []
            self.item_entries = []
            self.tracker['current-item'] = None

        elif self.gui_state in ['test-new:titem-edit', 'test-new:titem-new']:
            self.gui_state = 'test-new'
            self.item_keys = []
            self.item_entries = []
            self.tracker['current-item'] = None

        elif self.gui_state in ['item-new', 'item-edit', 'titem-edit']:
            self.gui_state = 'ready'
            self.item_keys = []
            self.item_entries = []
            self.tracker['current-item'] = None

        elif self.gui_state in ['pers-new', 'pers-edit']:
            self.gui_state = 'ready'
            self.pers_keys = []
            self.pers_entries = []
            self.tracker['current-pers'] = None

        elif self.gui_state in ['pers-import', 'pers-compare']:
            self.gui_state = 'ready'

        elif self.gui_state in ['rent-adv']:
            self.tracker['current-pers'] = None
            self.gui_state = 'ready'

        elif "?delete" == self.gui_state[-7:]:
            self.gui_state = self.gui_state.split('?')[0]
            self.tracker['deleting'] = None
            self.tracker['deleting-idd'] = None
            self.tracker['deleting-ite'] = None
            
        elif "?rdelete" == self.gui_state[-8:]:
            self.gui_state = self.gui_state.split('?')[0]

        elif '-resource' == self.gui_state[-9:]:
            self.writeDescription()
            self.gui_state = 'ready'
            self.tracker['chosen-test'] = None
            self.tracker['chosen-item'] = None
            self.tracker['choose-list'] = None

        elif '-his' == self.gui_state[-4:]:
            self.gui_state = 'ready'
            self.tracker['chosen-history'] = None

        elif 'dept-export' == self.gui_state:
            self.gui_state = 'ready'            
            
        else:
            print "\n\n Unknown window aborted!\n"
            print self.gui_state, self.tmp_dialog[-1].title
        self.destroy_tmp()

    #========================================================================================================
    #                               HISTORY
    #========================================================================================================


    def printPersonHistoryClicked(self, widget = None):
        if not self.check_gui_transition('pers-his'):
            print "abnormal gui transition! '" + str(self.gui_state) + ' "pers-his"'
            return
        self.gui_state = 'pers-his'
        self.historyDialogPopUp(self.person_view)

    def printItemHistoryClicked(self, widget = None):
        if not self.check_gui_transition('item-his'):
            print "abnormal gui transition! '" + str(self.gui_state) + ' "item-his"'
            return
        self.gui_state = 'item-his'
        self.historyDialogPopUp(self.item_view)        

    def printTestHistoryClicked(self, widget = None):
        if not self.check_gui_transition('test-his'):
            print "abnormal gui transition! '" + str(self.gui_state) + ' "test-his"'
            return
        self.gui_state = 'test-his'
        self.historyDialogPopUp(self.test_view)
        
        
    def historyDialogPopUp(self, view):        
        (model, ite) = view.get_selection().get_selected()
        if ite == None:
            self.gui_state = 'ready'
            return
        
        o_id = model.get_value(ite, 0)
        obj = self.config[o_id]
        mode = obj['ID'][:4].lower()
        
        self.tracker['chosen-history'] = obj
        print "main_window.historyDialogPopUp():", obj

        dialog = gtk.Dialog(title="Historia".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        dialog.set_size_request(750, 450)
        # stworzyć widok, uzupełnić danymi, labelka z nazwą / imieniem nazwiskiem

        if mode == 'pers':
            label = gtk.Label( obj['pers:name'] + " " + obj['pers:lname'])
        else:
            label = gtk.Label( obj[mode + ':name'])
            
        dialog.vbox.pack_start(label, False, False, 2)
        label.show()
        
        window = gtk.ScrolledWindow()
        self.currentstore = gtk.ListStore(str, str, str, str)

        if mode == 'pers':
            columns = [("przedmiot", 0), ("czynność", 1), ("kiedy", 2), ("sygnatura", 3)]
            rows = obj['rent_old']
        else:
            columns = [("sygnatura", 0), ("czynność", 1), ("kiedy", 2), ("komu", 3)]
            rows = obj['history'] # tutaj zamienić na sumę przedmiotów
            
        for r in rows:
            if columns[0][0] == "przedmiot":
                r[0] = self.config[r[0]]['item:name']
            elif r[3] != "":
                r[3] = self.config[r[3]]['pers:name'] + " " + self.config[r[3]]['pers:lname']
            self.currentstore.append(r) # tutaj podmienić wartość pod ID
            
        treeview = gtk.TreeView(self.currentstore)
        
        for i in range(len(columns)):
            tvcolumn = gtk.TreeViewColumn(columns[i][0].decode("cp1250").encode("UTF-8"))
            treeview.append_column(tvcolumn)
            cell = gtk.CellRendererText()
            tvcolumn.pack_start(cell, True) # True = expand
            tvcolumn.add_attribute(cell, 'text', columns[i][1])
            tvcolumn.set_sort_column_id(columns[i][1])
        window.add(treeview)
        self.currentview = treeview
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.show()

        dialog.vbox.pack_start(window, True, True, 2)
        treeview.show()

        modes = [("Cofnij", self.abort)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            dialog.action_area.pack_start(button, True, True, 3)

        dialog.show()


    #========================================================================================================
    #                               ITEM
    #========================================================================================================

    def createItemButton(self, widget = None):
        # przycisk w oknie głównym
        if not self.check_gui_transition('item-new'):
            print "abnormal gui transition! '" + str(self.gui_state) + ' "item-new"'
            return
        self.gui_state = 'item-new'
        self.openNewTestItemDialogPopUp("Tworzenie przedmiotu")
        

    def editItemButton(self, widget = None):
        # przycisk w oknie głównym
        if not self.check_gui_transition('item-edit'):
            print "abnormal gui transition! '" + str(self.gui_state) + ' "item-edit"'
            return

        # srawdzić wybrany
        (model, ite) = self.item_view.get_selection().get_selected()
        if ite == None:
            return
        i_id = model.get_value(ite, 0)
        item = self.config[i_id]
        
        self.tracker['current-item'] = item

        # jeśli testowy inne zachowanie
        if item['test'] != "":
            self.gui_state = 'titem-edit'
            d_title = "Edycja przedmiotu testowego"
        else:
            self.gui_state = 'item-edit'
            d_title = "Edycja przedmiotu"
        self.openNewTestItemDialogPopUp(d_title)

    def createTestItemClicked(self, widget = None):
        if not self.check_gui_transition(self.gui_state + ":titem-new"):
            print "abnormal gui transition! '" + str(self.gui_state) + '"' + self.gui_state + ':titem-new"'
            return
        self.gui_state += ":titem-new"
        #self.tracker['current-item'] = {}
        self.openNewTestItemDialogPopUp("Tworzenie przedmiotu testowego")


    def editTestItemClicked(self, widget = None):
        (model, ite) = self.currentview.get_selection().get_selected()
        if ite == None:
            return
        if not self.check_gui_transition(self.gui_state + ":titem-edit"):
            print "abnormal gui transition! '" + str(self.gui_state) + '"' + self.gui_state + ':titem-edit"'
            return
        self.gui_state += ":titem-edit"
        idd = model.get_value(ite, 0)
        index = self.tracker['current-test-item-ids'].index(idd)
        self.tracker['current-item'] = self.tracker['current-test']['items'][index]
        self.tracker['current-item-idd'] = idd
        self.tracker['current-item-ite'] = ite
        pprint.pprint(self.tracker['current-item'])

        self.openNewTestItemDialogPopUp("Edycja przedmiotu testowego")     

    def deleteTestItemClicked(self, widget = None):
        (model, ite) = self.currentview.get_selection().get_selected()
        if ite == None:
            return
        idd = model.get_value(ite, 0)
        index = self.tracker['current-test-item-ids'].index(idd)
        item = self.tracker['current-test']['items'][index]
        self.tracker['deleting'] = item
        self.tracker['deleting-idd'] = idd
        self.tracker['deleting-ite'] = ite
        self.delete_approve()

    def deleteItemClicked(self, widget = None):
        # srawdzić wybrany
        (model, ite) = self.item_view.get_selection().get_selected()
        if ite == None:
            return
        i_id = model.get_value(ite, 0)
        item = self.config[i_id]        
        self.tracker['deleting'] = item
        self.delete_approve()

     

    def deleteItemApproved(self, widget = None):
        # tylko dla kasowania z subokna
        subwindow = 'test' in self.gui_state
        
        if subwindow:
            index = self.tracker['current-test-item-ids'].index(self.tracker['deleting-idd'])
            self.tracker['current-test']['items'].pop(index)
            self.tracker['current-test-item-ids'].pop(index)
            self.currentstore.remove(self.tracker['deleting-ite'])
        else:
            titem = self.tracker['deleting']['test'] != ""
            if titem:
                t_id = self.tracker['deleting']['test']
                i_id = self.config.deleteItem(self.tracker['deleting']['ID'], True)
                self.removeItemRows([i_id])
                self.updateTestRow(t_id)
            else:
                self.config.deleteItem(self.tracker['deleting']['ID'], True)
                self.removeItemRows([self.tracker['deleting']['ID']])
        self.abort(widget)

    def delete_approve(self, widget = None, event = None, data = None):
        self.gui_state += "?delete"
        print self.gui_state
        dialog = gtk.Dialog(title="Usuwanie przedmiotu.".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)


        rented = False
        rented_list = []

        if self.tracker['deleting']['out']:
            for out in self.tracker['deleting']['out']:
                rented_list.append(self.tracker['deleting']['item:name'] + "  wypożyczone przez: ".decode("cp1250").encode("UTF-8") +
                                   self.config[out[3]]['pers:name'] + " " + self.config[out[3]]['pers:lname'])
            rented = True
        
        if rented:
            print "jesli cos wypozyczone"
            info = "Usunięcie niemożliwe ponieważ:\n".decode("cp1250").encode("UTF-8") + "\n".join(rented_list)
            label = gtk.Label(info)
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()
            
            b2 = gtk.Button("Cofnij")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()            
        else:
            
            label = gtk.Label("Czy chcesz usunąć przedmiot:\n".decode("cp1250").encode("UTF-8") + self.tracker['deleting']['item:name'])
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()

            b1 = gtk.Button("Tak")
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.deleteItemApproved)
            b1.show()
            
            b2 = gtk.Button("Nie")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()

        dialog.show()        
        return True
        
    def openNewTestItemDialogPopUp(self, widget = None, d_title = ""):
        self.updateTracker()

        dialog = gtk.Dialog(title=d_title.decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)        
                    
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        
        existing = "item-edit" in self.gui_state
        titem = "titem" in self.gui_state


        dialog.set_size_request(750, 450)
        primary = ["    Nazwa: ", "    Autor: ", "    Wydawnictwo: " ]
        keys    = ['item:name', 'author', 'publisher']
        entries = []

        hbox1 = gtk.HBox(True, 0)
        hbox1.set_homogeneous(False)
        for i in range(len(primary)):
            if existing:
                default = self.tracker['current-item'][keys[i]]
            else:
                default = ""
            label = gtk.Label(primary[i].decode("cp1250").encode("UTF-8"))
            hbox1.pack_start(label, False, False, 2)
            label.show()
            
            entry = gtk.Combo()
            entry.set_popdown_strings([default] + self.tracker[keys[i]])

            
            entries.append(entry)
            hbox1.pack_start(entry, True, True, 2)
            entry.show()


        dialog.vbox.pack_start(hbox1, False, True, 2)            
        hbox1.show()
        self.item_keys = keys

        group = ["    Kategoria: ", "    Pożądany zapas: "]
        keys = ['category', 'desired']

        hbox2 = gtk.HBox(True, 0)
        
        for i in range(len(group)):

            label = gtk.Label(group[i].decode("cp1250").encode("UTF-8"))
            hbox2.pack_start(label, False, False, 2)
            label.show()

            
            if i == 0:
                entry = gtk.Combo()
                
                entry.set_value_in_list(True, False)
                if titem:
                    if existing:
                        if self.tracker['current-item']['category'] in self.config.not_tracked_items:
                            cat_list = self.config.not_tracked_items
                        else:
                            cat_list = self.config['#ITEM_TYPE_LIST_1']
                            cat_list.pop(3)

                    else:
                        cat_list = self.config['#ITEM_TYPE_LIST_1']
                else:
                    cat_list = self.config['#ITEM_TYPE_LIST_2']
                entry.set_popdown_strings(cat_list)
                if existing:

                    if 'ID' in self.tracker['current-item'].keys():
                        entry.entry.set_text(self.tracker['current-item']['category'])
                    else:                                             
                        entry.entry.set_text(self.tracker['current-item'][keys[i]])
            else:
                if existing:
                    default = int(self.tracker['current-item'][keys[i]])
                else:
                    default = 1
                adj = gtk.Adjustment(default, 0, 99999, 1, 10)
                entry = gtk.SpinButton(adj, 1.0)
            
            entries.append(entry)
            hbox2.pack_start(entry, True, True, 2)
            entry.show()

        self.item_keys += keys

        dialog.vbox.pack_start(hbox2, False, True, 2)            
        hbox2.show()

        describe = ['Opis:', 'Dane dodatkowe:']
        keys = ['item:public', 'item:private']
        for i in range(len(describe)):
            label = gtk.Label(describe[i].decode("cp1250").encode("UTF-8"))
            dialog.vbox.pack_start(label, False, True, 2)
            label.show()

            window = gtk.ScrolledWindow()

            entry = gtk.TextView()
            entry.set_editable(True)
            if existing:
                default = self.tracker['current-item'][keys[i]]
            else:
                default = ""
            entry.get_buffer().set_text(default)    
            entry.set_wrap_mode(gtk.WRAP_WORD)

            window.add(entry) 
            window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            window.set_shadow_type(gtk.SHADOW_IN)
            window.show()
            
            dialog.vbox.pack_start(window, True, True, 2)
            entry.show()

            entries.append(entry.get_buffer())
        
        self.item_keys += keys
        self.item_entries = entries

        if existing:
            b1 = gtk.Button("Zapisz".decode("cp1250").encode("UTF-8"))
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.editItem)
            b1.show()
            
        else:
            b1 = gtk.Button("Stwórz".decode("cp1250").encode("UTF-8"))
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.createItem)
            b1.show()
            
        b2 = gtk.Button("Cofnij")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.abort)
        b2.show()

        dialog.show()


    #========================================================================================================
    #                               ITEM - FINISHING
    #========================================================================================================
    

    def editItem(self, widget = None):
        self.updateTracker()
        data = {}      
        
        for k, e in map(lambda x,y: (x,y), self.item_keys, self.item_entries):
            if isinstance(e, gtk.SpinButton):
                data[k] = e.get_value_as_int()
                continue
            try:
                string = e.entry.get_text()
                string = string.replace("\n", " ")
                data[k] = string
            except:
                data[k] = e.get_text(e.get_start_iter(), e.get_end_iter())

        self.item_keys = []
        self.item_entries = []
                
        item = self.tracker['current-item']
        self.tracker['current-item'] = None
        
        for k in data.keys():
            item[k] = data[k]

        titem = 'titem' in self.gui_state
        subwindow = 'test' in self.gui_state
        
        if titem:
            if subwindow:
                ite = self.tracker['current-item-ite']
                self.tracker['current-item-ite'] = None
                idd = self.tracker['current-item-idd']
                self.tracker['current-item-idd'] = None

                view_keys = ["item:name", "author", "publisher", 'category', 'desired']

                for i in range(1, len(view_keys)+1):
                    self.currentstore.set_value(ite, i, item[view_keys[i-1]])
                self.gui_state = self.gui_state.split(':')[0]
            else:
                i_id = self.config.editItem(item)
                self.updateItemRow(i_id)
                self.updateTestRow(item['test'])
                self.gui_state = 'ready'
        else:
            i_id = self.config.editItem(item)
            self.updateItemRow(i_id)
            self.gui_state = 'ready'

        print "Zakończono edycję przedmiotu:"
        pprint.pprint(item)

        self.destroy_tmp()            

    
    def createItem(self, widget = None):
        self.updateTracker()
        data = {}      
        
        for k, e in map(lambda x,y: (x,y), self.item_keys, self.item_entries):
            if isinstance(e, gtk.SpinButton):
                data[k] = e.get_value_as_int()
                continue
            try:
                string = e.entry.get_text()
                string = string.replace("\n", " ")
                data[k] = string
            except:
                data[k] = e.get_text(e.get_start_iter(), e.get_end_iter())

        self.item_keys = []
        self.item_entries = []
        
        titem = 'titem' in self.gui_state
        subwindow = 'test' in self.gui_state

        
        if titem:
            self.tracker['current-test']['items'].append(data)
            iid = time.time() + 10000
            self.tracker['current-test-item-ids'].append(iid)
            
            view_keys = ["item:name", "author", "publisher", 'category', 'desired']
   
            tmp = [iid]
            
            for k in view_keys:
                tmp.append(str(data[k]))
            self.currentstore.append(tmp)
            self.gui_state = self.gui_state.split(':')[0]
        else:            
            i_id = self.config.addItem(data)
            self.item_store.append(self.createItemRow(i_id))
            self.gui_state = 'ready'
            
        self.destroy_tmp()

    #========================================================================================================
    #                               UPDATING VIEWS
    #========================================================================================================

    def updateItemRow(self, i_id):
        tmp = self.createItemRow(i_id)
        for i in range(len(self.item_store)):
            if self.item_store[i][0] == i_id:
                self.item_store[i] = tmp
                return
        self.item_store.append(tmp)        
        

    def removeItemRows(self, i_id_list):
        delete = []
        for i in range(len(self.item_store)):
            if self.item_store[i][0] in i_id_list:
                delete[0:0] = [i]
        
        for i in delete:
            del self.item_store[i]                                                  

    def updateTestRow(self, t_id):
        tmp = self.createTestRow(t_id)
        for i in range(len(self.test_store)):
            if self.test_store[i][0] == t_id:
                self.test_store[i] = tmp
                return
        self.test_store.append(tmp)

    def removeTestRow(self, t_id):        
        for i in range(len(self.test_store)):
            if self.test_store[i][0] == t_id:
                del self.test_store[i]
                return

    #========================================================================================================
    #                               Tracker
    #========================================================================================================

    def updateTracker(self):
        """
        Pobieranie danych z kontrolek okien i przesyłanie do trackera. Po zakończeniu operacji tracker posiada
        aktualne dane przedmiotu w swoich kluczach i można wykorzystać go do zapisu do bazy danych.
        """
        keys = self.test_keys + self.item_keys + self.pers_keys
        entries = self.test_entries + self.item_entries + self.pers_entries
        for k, e in map(lambda x,y: (x,y), keys, entries):
            if k in self.tracker.known_keys:
                if isinstance(e, gtk.Combo):
                    e = e.entry                    
                try:
                    string = e.get_text()
                    string = string.replace("\n", " ")
                    self.tracker[k] = string
                except:
                    self.tracker[k] = e.get_text(e.get_start_iter(), e.get_end_iter())

    #========================================================================================================
    #                               PERSON
    #========================================================================================================

    def importPersonListClicked(self, widget = None):
        """
        Naciśnięcie przycisku importowania danych o studentach. Otwiera okno wyboru pliku CSV.
        """
        if not self.check_gui_transition('pers-import'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'pers-import'"
            return
        self.gui_state = 'pers-import'
        print self.gui_state
        
        dialog = gtk.FileSelection("Wybierz plik z listą studentów".decode("cp1250").encode("UTF-8"))
        dialog.set_modal(True)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        self.tmp_dialog.append(dialog)
        dialog.ok_button.connect('clicked', self.importPersonListChosen)
        dialog.cancel_button.connect('clicked', self.abort)
        dialog.complete("*.csv")
        dialog.hide_fileop_buttons()
        dialog.set_select_multiple(False)
        dialog.show()

    def importPersonListChosen(self, widget = None):
        """
        Importowanie danych z pliku CSV. Konwersja kodowania (converter).
        """
        dialog = self.tmp_dialog[-1]
        import_file = dialog.get_filename()
        try:
            lines = open(import_file, 'r').readlines()            
        except Exception, e:
            print e
            return
        lines = converter.extract(lines)
        #print lines

        self.destroy_tmp()
        self.comparePersonListPopUp(lines)

    def comparePersonListPopUp(self, lines):
        """
        Importowanie danych do bazy:
        1. stworzenie słownika {index: {słownik z danymi o studencie} }
        2. dla każdej osoby z bazy danych odszukanie w słowniku i:
            a) jeśli występuje -- aktualizacja danych
            b) jeśli nie występuje i nie ma wypożyczeń -- usunięcie
            c) wpp zaznaczenie do usunięcia
        """
        ##### porawne - do odkomentowania!
        if not self.check_gui_transition('pers-compare'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'pers-compare'"
            return
        self.gui_state = 'pers-compare'
        print self.gui_state
        dialog = gtk.Dialog(title="Dodawanie / aktualizacja kont".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)

        dialog.set_transient_for(self.window)
        i = 0
        lb = ""

        label = gtk.Label("   Czekaj ...   ".decode("cp1250").encode("UTF-8"))
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()

        dialog.show()

        # lista indeksów starych... ind->id, nowy dodać, stary zaktualizować (rok), nieobecne usunąć/zaznaczyć do usunięcia
        start_person_dict = {}
        for person_id in self.config['#PERS_LIST']:
            start_person_dict[self.config[person_id]['indx']] = person_id
        
        updated = 0
        new = 0
        new_ids = []
        deleted = 0
        deleted_ids = []
        
        for r in lines:
            if r in start_person_dict:
                print "year update for:", start_person_dict[r], "from", self.config[start_person_dict[r]]['year'], "to", lines[r]['year']
                self.config[start_person_dict[r]]['year'] = lines[r]['year']
                del start_person_dict[r]
                updated += 1
            else:
                print "new:", lines[r]
                new_ids.append(self.config.addPerson(lines[r], False))
                new += 1

        
        for indx in start_person_dict:
            p_id = start_person_dict[indx]
            print "to be deleted:", p_id
            if 'year' not in self.config[p_id].keys():
                continue
            elif self.config[p_id]['rent']:
                marked = self.config[p_id]
                marked['year'] = "DO USUNIĘCIA".decode("cp1250").encode("UTF-8")
                self.config[p_id] = marked
                self.updatePersonRow(p_id)
                print "MARKED:", p_id
                print self.config[p_id]
            else:
                self.config.deletePerson(p_id, False)
                self.removePersonRow(p_id)
                deleted += 1
                print "Deleted:", p_id
                print self.config[p_id]

        self.config.sync()
        for p_id in new_ids:
            self.updatePersonRow(p_id)
        
        self.gui_state = 'ready'
        final_text = "  Zakończono:\n    nowe: %i,\n    uaktualnione: %i,\n    usunięte: %i.\n\n\n  Możesz zamknąć to okno." % (new, updated, deleted)
        label.set_text(final_text.decode("cp1250").encode("UTF-8"))
            
    def deletePersonClicked(self, widget = None):
        """
        Naciśnięcie przycisku usunięcia osoby.
        """
        (model, ite) = self.person_view.get_selection().get_selected()
        if ite == None:
            return
        p_id = model.get_value(ite, 0)
        person = self.config[p_id]        
        self.tracker['deleting'] = person
        self.delete_person_approve()

    def deletePersonApproved(self, widget = None):
        """
        Potwierdzenie usunięcia: usunięcie z bazy danych, aktualizacja widoku
        """
        person = self.tracker['deleting']
        p_id = self.config.deletePerson(person['ID'])
        self.removePersonRow(person['ID'])

        self.abort(widget)

    def delete_person_approve(self, widget = None, event = None, data = None):
        """
        Okno potwierdzenia usunięcia. Jeśli osoba ma coś wypożyczone to tylko informacja o zakazaniu operacji (wraz z podaniem przyczyny)
        """
        self.gui_state += "?delete"
        print self.gui_state
        dialog = gtk.Dialog(title="Usuwanie konta.".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)

        if self.tracker['deleting']['rent']:
            label = gtk.Label("Usunięcie konta niemożliwe - ta osoba posiada wypożyczone przedmioty.".decode("cp1250").encode("UTF-8"))
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()
            
            b2 = gtk.Button("Cofnij")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()

        else:
            label = gtk.Label("Czy chcesz usunąć konto tej osoby:\n".decode("cp1250").encode("UTF-8") +
                              self.tracker['deleting']['pers:name'] + " " + self.tracker['deleting']['pers:lname'])
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()

            b1 = gtk.Button("Tak")
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.deletePersonApproved)
            b1.show()
            
            b2 = gtk.Button("Nie")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()

        dialog.show()        
        return True

    
    def openEditPersonDialogPopUp(self, widget = None):
        """
        Przycisk "Edytuj" dla osoby
        """
        (model, ite) = self.person_view.get_selection().get_selected()
        if ite == None:
            return
        if not self.check_gui_transition('pers-edit'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'pers-edit'"
            return
        self.gui_state = 'pers-edit'

        p_id = model.get_value(ite, 0)

        person = self.config[p_id]

        pprint.pprint(person)
        self.tracker['current-pers'] = person
       
        d_title = "Edycja konta".decode("cp1250").encode("UTF-8")
        if 'position' in person.keys():
            student = False
        else:
            student = True
        self.personDialogPopUp(None, d_title, student)
        
    def openNewPersonDialogPopUp(self, widget = None):
        """
        Przycisk "Stwórz nowe konto studenckie"
        """

        if not self.check_gui_transition('pers-new'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'pers-new'"
            return
        self.gui_state = 'pers-new'

        self.tracker['current-pers'] = {'rent': []}

        d_title = "Tworzenie nowego konta".decode("cp1250").encode("UTF-8")

        self.personDialogPopUp(None, d_title)

    def openOuterNewPersonDialogPopUp(self, widget = None):
        """
        Przycisk "Stwórz nowe konto pracownika"
        """

        if not self.check_gui_transition('pers-new'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'pers-new'"
            return
        self.gui_state = 'pers-new'

        self.tracker['current-pers'] = {'rent': []}

        d_title = "Tworzenie nowego konta".decode("cp1250").encode("UTF-8")

        self.personDialogPopUp(None, d_title, False)


    def personDialogPopUp(self, widget = None, d_title = "Konto", student = True):
        """
        Okno edycji osoby. Dane osobowe i lista wypożyczonych przedmiotów. Umożliwia dokonanie zwrotu wypozyczeń.
        """

        dialog = gtk.Dialog(title=d_title, parent=self.window, 
                            flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        
        dialog.set_size_request(750, 550)
        primary_l = [[" Uczelnia: "," Wydział: "],["    Imię: ", "    Nazwisko: "], ["            Adres stały: "], [" Adres tymczasowy: "],
                     [" Telefon: ", " e-mail: "]]
        keys_l    = [['univ','faculty'], ['pers:name', 'pers:lname'], ['ad:main'], ['as:addi'], ['phone','e-mail']]
        entries = []
        self.pers_keys = []
        existing = 'ID' in self.tracker['current-pers'].keys()

        for i in range(len(primary_l)):
            hbox1 = gtk.HBox(True, 0)
            hbox1.set_homogeneous(False)
            primary = primary_l[i]
            keys = keys_l[i]
            if i == 1:
                hbox2 = gtk.HBox(True, 0)
                hbox2.set_homogeneous(False)
                if student:
                    for m in [(" Studia: ", 's:type'),(" Nr. indeksu: ", 'indx'),(" Rok:", 'year')]:
                        label = gtk.Label(m[0].decode("cp1250").encode("UTF-8"))
                        hbox2.pack_start(label, False, False, 2)
                        label.show()
                        if m[1] == 's:type':
                            entry = gtk.Combo()
                            if existing:
                                entry.set_popdown_strings([self.tracker['current-pers'][m[1]]] + ["stacjonarne", "wieczorowe", "doktoranckie", "podyplomowe"])
                            else:
                                entry.set_popdown_strings(["stacjonarne", "wieczorowe", "doktoranckie", "podyplomowe"])
                        else:
                            entry = gtk.Entry()
                            if existing:
                                entry.set_text(self.tracker['current-pers'][m[1]])
                        entries.append(entry)

                        hbox2.pack_start(entry, True, True, 2)
                        
                        entry.show()
                    self.pers_keys += ['s:type', 'indx', 'year']
                else:
                    for m in [(" Adres uczelni: ", 'ad:univ'),(" Stanowisko: ", 'position'),(" Dokument: ", 'indx')]:
                        label = gtk.Label(m[0].decode("cp1250").encode("UTF-8"))
                        hbox2.pack_start(label, False, False, 2)
                        label.show()
                        if m[1] == 's:type':
                            entry = gtk.Combo()
                            entry.set_popdown_strings(["stacjonarne", "wieczorowe", "doktoranckie", "podyplomowe"])
                        else:
                            entry = gtk.Entry()
                        entries.append(entry)

                        hbox2.pack_start(entry, True, True, 2)
                        entry.show()
                    self.pers_keys += ['ad:univ', 'position', 'indx']
                        
                
                dialog.vbox.pack_start(hbox2, False, True, 2)            
                hbox2.show()            
            for j in range(len(primary)):
                label = gtk.Label(primary[j].decode("cp1250").encode("UTF-8"))
                hbox1.pack_start(label, False, False, 2)
                label.show()
            
                entry = gtk.Entry()
                if existing:
                    default = self.tracker['current-pers'][keys[j]]
                elif i == 0:
                    if j == 0:
                        default = "Uniwersytet Wrocławski".decode("cp1250").encode("UTF-8")
                    else:
                        default = "WNHiP".decode("cp1250").encode("UTF-8")
                else:
                    default = ""
                #entry.set_popdown_strings([default] + self.tracker[keys[j]])
                entry.set_text(default)
                
                entries.append(entry)

                hbox1.pack_start(entry, True, True, 2)
                entry.show()
            self.pers_keys += keys

            dialog.vbox.pack_start(hbox1, False, True, 2)            
            hbox1.show()

        describe = ['Dane dodatkowe:']
        keys = ['pers:desc']
        for i in range(len(describe)):
            label = gtk.Label(describe[i].decode("cp1250").encode("UTF-8"))
            dialog.vbox.pack_start(label, False, True, 2)
            label.show()

            window = gtk.ScrolledWindow()

            entry = gtk.TextView()
            entry.set_editable(True)

            if existing:
                default = self.tracker['current-pers'][keys[i]]
            else:
                default = ""
            
            
            entry.get_buffer().set_text(default)
            entry.set_wrap_mode(gtk.WRAP_WORD)

            window.add(entry)
            window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            window.set_shadow_type(gtk.SHADOW_IN)
            window.show()
            
            dialog.vbox.pack_start(window, True, True, 2)
            entry.show()

            entries.append(entry.get_buffer())
        self.pers_keys += keys
        self.pers_entries = entries

        window = gtk.ScrolledWindow()
        self.currentstore = gtk.ListStore(str, str, str, str, str)
        
        view_names = ["ID", "test", "nazwa", "syg", "Termin oddania"]
        #view_indx  = [      0,       3,     1 ]    
        

        for r in self.tracker['current-pers']['rent']:
            #for k in view_keys:
            #    tmp.append(str(i[k]))
            item = self.config[r[0]]
            if item['test'] != "":
                test = self.config[item['test']]['test:name']
            else:
                test = ""
            self.currentstore.append([r[0], test, self.config[r[0]]['item:name'], r[3], r[2]])
        
        treeview = gtk.TreeView(self.currentstore)
        for i in range(1, len(view_names)):
            tvcolumn = gtk.TreeViewColumn(view_names[i].decode("cp1250").encode("UTF-8"))
            treeview.append_column(tvcolumn)
            cell = gtk.CellRendererText()
            tvcolumn.pack_start(cell, True) # True = expand
            tvcolumn.add_attribute(cell, 'text', i)
            tvcolumn.set_sort_column_id(i)

        frame = gtk.Frame("Wypożyczone przedmioty:".decode("cp1250").encode("UTF-8"))
        window.add(treeview)
        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.currentview = treeview
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.show()
        frame.add(window)
        frame.show()

        dialog.vbox.pack_start(frame, True, True, 2)
        treeview.show()

        box = gtk.HBox(False, 3)
        modes = [(" Zwrot ", self.returnItem)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            box.pack_start(button, True, True, 3)        

        box.show()
        dialog.vbox.pack_start(box, False, False, 2)

        modes = [("Zatwierdź", self.writePerson), ("Cofnij", self.abort)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            dialog.action_area.pack_start(button, True, True, 3)

        dialog.show()

    def returnItem(self, widget = None):
        (model, ite_l) = self.currentview.get_selection().get_selected_rows()
        if not ite_l:
            return
        ite_l.reverse()
        for ite in ite_l:
            ite = model.get_iter(ite)            
            # sprawdzić czy modyfikacja czasu nie pada!
            i_id = model.get_value(ite, 0)
            sig = model.get_value(ite, 3)
            print i_id, sig

            item = self.config[i_id]
            person = self.tracker['current-pers']
            del model[ite]

            first_date = "9999"
            inx = 0
            while inx < len(person['rent']):
                r = person['rent'][inx]
                if r[3] == sig:
                    returned = person['rent'].pop(inx)
                    print "Usunięcie wypożyczenia z listy:", returned
                    returned[1] = "zwrot"
                    returned[2] = self.time2string(time.time())
                    person['rent_old'].append(returned)
                    
                else:
                    inx += 1                
                    if r[2] < first_date:
                        first_date = r[2]

            if first_date == "9999":
                first_date = ""
            person['rent_date'] = first_date
            self.updatePersonRow(person['ID'])
            p_id = person['ID']
            self.config[p_id] = person


            for inx in range(len(item['out'])):
                r = item['out'][inx]
                if r[0] == sig:
                    returned = item['out'].pop(inx)
                    returned[1] = 'zwrot'
                    returned[2] = self.time2string(time.time())
                    item['history'].append(returned)
                    print "end"
                    break
                
            for inx in range(len(item['Q'])):
                r = item['Q'][inx]
                print "now:", r
                if r[0] == sig:
                    item['Q'][inx] = item['Q'][inx][:2]
                    break
            self.config[i_id] = item
            self.updateItemRow(i_id)
            if item['test'] != "":
                self.updateTestRow(item['test'])

        self.config.sync()
        

    #========================================================================================================
    #                               PERSON - FINISHING
    #========================================================================================================
    def writePerson(self, widget = None):
        self.updateTracker()
        
        for k, e in map(lambda x,y: (x,y), self.pers_keys, self.pers_entries):
            if isinstance(e, gtk.Combo):
                e = e.entry
            try:
                string = e.get_text()
                string = string.replace("\n", " ")
                self.tracker['current-pers'][k] = string
            except:
                self.tracker['current-pers'][k] = e.get_text(e.get_start_iter(), e.get_end_iter())

                    
        print "Dane do zapisania:"
        pprint.pprint(self.tracker['current-pers'])
        print "\n"
        
        existing = 'ID' in self.tracker['current-pers'].keys()
        if existing:
            p_id = self.config.editPerson(self.tracker['current-pers'])
            self.updatePersonRow(p_id)
        else:
            p_id = self.config.addPerson(self.tracker['current-pers'])
            self.person_store.prepend(self.createPersonRow(p_id))

        pprint.pprint(self.config[p_id])

        self.abort()
        
    def updatePersonRow(self, p_id):
        tmp = self.createPersonRow(p_id)
        for i in range(len(self.person_store)):
            if self.person_store[i][0] == p_id:
                self.person_store[i] = tmp
                return
        self.person_store.append(tmp)

    def removePersonRow(self, p_id):        
        for i in range(len(self.person_store)):
            if self.person_store[i][0] == p_id:
                del self.person_store[i]
                return

    #========================================================================================================
    #                               TEST
    #========================================================================================================

    def deleteTestClicked(self, widget = None):
        (model, ite) = self.test_view.get_selection().get_selected()
        if ite == None:
            return
        t_id = model.get_value(ite, 0)
        test = self.config[t_id]        
        self.tracker['deleting'] = test
        self.delete_test_approve()

    def deleteTestApproved(self, widget = None):
        # tylko dla kasowania z subokna
        
        test = self.tracker['deleting']
        t_id, items = self.config.deleteTest(test['ID'])
        self.removeTestRow(test['ID'])
        self.removeItemRows(items)

        self.abort(widget)
        
    def delete_test_approve(self, widget = None, event = None, data = None):
        self.gui_state += "?delete"
        print self.gui_state
        dialog = gtk.Dialog(title="Usuwanie testu.".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)

        rented = False
        rented_list = []

        for i_id in self.tracker['deleting']['items']:
            if self.config[i_id]['out']:
                for out in self.config[i_id]['out']:
                    rented_list.append(self.config[i_id]['item:name'] + "  wypożyczone przez: ".decode("cp1250").encode("UTF-8") +
                                       self.config[out[3]]['pers:name'] + " " + self.config[out[3]]['pers:lname'])
                rented = True

        if rented:
            print "jesli cos wypozyczone"
            info = "Usunięcie niemożliwe ponieważ:\n".decode("cp1250").encode("UTF-8") + "\n".join(rented_list)
            label = gtk.Label(info)
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()
            
            b2 = gtk.Button("Cofnij")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()
        else:
        
            label = gtk.Label("Czy chcesz usunąć test:\n".decode("cp1250").encode("UTF-8") + self.tracker['deleting']['test:name'])
            dialog.vbox.pack_start(label, True, True, 20)
            label.show()

            b1 = gtk.Button("Tak")
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.deleteTestApproved)
            b1.show()
            
            b2 = gtk.Button("Nie")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()

        dialog.show()        
        return True
    
    def openEditTestDialogPopUp(self, widget = None):
        (model, ite) = self.test_view.get_selection().get_selected()
        if ite == None:
            return
        if not self.check_gui_transition('test-edit'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'test-edit'"
            return
        self.gui_state = 'test-edit'

        t_id = model.get_value(ite, 0)

        test = self.config[t_id]
        items = []
        for i in test['items']:
            items.append(self.config[i])
        test['items'] = items

        pprint.pprint(test)
       
        self.tracker['current-test'] = test
        self.tracker['current-test-item-ids'] = []
        
        d_title = "Edycja testu (".decode("cp1250").encode("UTF-8") + self.tracker['current-test']['test:name'] +")"
        self.testDialogPopUp(None, d_title)
        
    def openNewTestDialogPopUp(self, widget = None):
        if not self.check_gui_transition('test-new'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'test-new'"
            return
        self.gui_state = 'test-new'

        self.tracker['current-test'] = {'items': []}
        self.tracker['current-test-item-ids'] = []

        d_title = "Tworzenie nowego testu (".decode("cp1250").encode("UTF-8") + str(self.config['#TEST_COUNT']) +")"

        self.testDialogPopUp(None, d_title)

    def testDialogPopUp(self, widget = None, d_title = ""):
        dialog = gtk.Dialog(title=d_title, parent=self.window, 
                            flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        
        dialog.set_size_request(750, 550)
        primary = ["    Nazwa: ", "    Autor: ", "    Wydawnictwo: " ]
        keys    = ['test:name', 'author', 'publisher']
        entries = []

        existing = 'ID' in self.tracker['current-test'].keys()
        
        hbox1 = gtk.HBox(True, 0)
        hbox1.set_homogeneous(False)
        for i in range(len(primary)):
            label = gtk.Label(primary[i].decode("cp1250").encode("UTF-8"))
            hbox1.pack_start(label, False, False, 2)
            label.show()
            
            entry = gtk.Combo()
            if existing:
                default = self.tracker['current-test'][keys[i]]
            else:
                default = ""
            entry.set_popdown_strings([default] + self.tracker[keys[i]])
            
            entries.append(entry)

            hbox1.pack_start(entry, True, True, 2)
            entry.show()
        self.test_keys = keys

        dialog.vbox.pack_start(hbox1, False, True, 2)            
        hbox1.show()
        
        group = ["Wybierz grupę:"]
        keys = ['group']

        hbox2 = gtk.HBox(True, 0)
        for i in range(len(group)):
            label = gtk.Label(group[i].decode("cp1250").encode("UTF-8"))
            hbox2.pack_start(label, False, True, 2)
            label.show()

            entry = gtk.Combo()
            
            if existing:
                default = [self.tracker['current-test'][keys[i]]] + self.config['#TEST_GROUP_LIST']
            else:
                default = self.config['#TEST_GROUP_LIST']
            entry.set_popdown_strings(default)
            
            entries.append(entry)
            hbox2.pack_start(entry, True, True, 2)
            entry.show()
        self.test_keys += keys

        dialog.vbox.pack_start(hbox2, False, True, 2)            
        hbox2.show()

        describe = ['Opis:', 'Dane dodatkowe:']
        keys = ['test:public', 'test:private']
        for i in range(len(describe)):
            label = gtk.Label(describe[i].decode("cp1250").encode("UTF-8"))
            dialog.vbox.pack_start(label, False, True, 2)
            label.show()

            window = gtk.ScrolledWindow()

            entry = gtk.TextView()
            entry.set_editable(True)

            if existing:
                default = self.tracker['current-test'][keys[i]]
            else:
                default = ""
            
            
            entry.get_buffer().set_text(default)
            entry.set_wrap_mode(gtk.WRAP_WORD)

            window.add(entry)
            window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            window.set_shadow_type(gtk.SHADOW_IN)
            window.show()
            
            dialog.vbox.pack_start(window, True, True, 2)
            entry.show()

            entries.append(entry.get_buffer())
        self.test_keys += keys


        window = gtk.ScrolledWindow()
        self.currentstore = gtk.ListStore(float, str, str, str, str, str)
        view_keys = ["item:name", "author", "publisher", 'category', 'desired']
        view_names = ["nazwa", "autor", "wydawnictwo", 'kategoria', 'pożądana ilość']
        
        index = 0
        for i in self.tracker['current-test']['items']:
            iid = time.time() + index
            tmp = [iid]
            self.tracker['current-test-item-ids'].append(iid)
            
            index += 1
            for k in view_keys:
                tmp.append(str(i[k]))
            self.currentstore.append(tmp)
        
        treeview = gtk.TreeView(self.currentstore)
        for i in range(len(view_keys)):
            tvcolumn = gtk.TreeViewColumn(view_names[i].decode("cp1250").encode("UTF-8"))
            treeview.append_column(tvcolumn)
            cell = gtk.CellRendererText()
            tvcolumn.pack_start(cell, True) # True = expand
            tvcolumn.add_attribute(cell, 'text', i+1)

        frame = gtk.Frame("Przedmioty należące do testu:".decode("cp1250").encode("UTF-8"))
        window.add(treeview)
        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_BROWSE)
        self.currentview = treeview
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.show()
        frame.add(window)
        frame.show()

        dialog.vbox.pack_start(frame, True, True, 2)
        treeview.show()
        self.test_entries = entries
        

        hbox3 = gtk.HBox(False, 10)
        modes = [("Stwórz nowy przedmiot", self.createTestItemClicked, 2), ("Edytuj zaznaczony przedmiot", self.editTestItemClicked, 2),
                 ("Usuń zaznaczony przedmiot", self.deleteTestItemClicked, 30)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            hbox3.pack_start(button, False, False, m[2])
            
        hbox3.show()
        
        dialog.vbox.pack_start(hbox3, False, False, 3)

        modes = [("Zatwierdź", self.writeTest), ("Cofnij", self.abort)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            dialog.action_area.pack_start(button, True, True, 3)

        dialog.show()

    #========================================================================================================
    #                               TEST - FINISHING
    #========================================================================================================

    def writeTest(self, widget = None):
        self.updateTracker()
        
        for k, e in map(lambda x,y: (x,y), self.test_keys, self.test_entries):
            try:
                string = e.entry.get_text()
                string = string.replace("\n", " ")
                self.tracker['current-test'][k] = string
            except:
                self.tracker['current-test'][k] = e.get_text(e.get_start_iter(), e.get_end_iter())

        t_id = self.config.addTest(self.tracker['current-test'])

        if isinstance(t_id, tuple) and self.gui_state == 'test-edit':
            # test był edytowany
            # usunąć przedmioty z listy 1 i 2
            self.removeItemRows(self.config[t_id[0]]['items'] + t_id[1])

            t_id = t_id[0]
            # usunąć test
        self.updateTestRow(t_id)
            
        for i_id in self.config[t_id]['items']:
            self.item_store.prepend(self.createItemRow(i_id))

        pprint.pprint(self.config[t_id])

        self.abort()
    


#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                               REST
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def notImplemented(self, widget = None, data = None):
        print "\n\nnot implemented!", widget, data, "\n"

    def main(self):
        gtk.main()

    def delete_event(self, widget, event = None, data = None):
        dialog = gtk.Dialog(title="Zakończ program?".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.destroy_tmp)
        label = gtk.Label("Zakończyć działanie programu?".decode("cp1250").encode("UTF-8"))
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()

        b1 = gtk.Button("Tak")
        dialog.action_area.pack_start(b1, True, True, 3)
        b1.connect('clicked', self.destroy)
        b1.show()
        
        b2 = gtk.Button("Nie")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.destroy_tmp)
        b2.show()

        dialog.show()        
        return True        

    def destroy(self, widget, data = None):
        """Zakończenie aplikacji"""
        print "destroy"
        self.wiki_thread.ssq.put('QUIT')
        self.config.closeFile()        
        ### stop wiki
        gtk.main_quit()


    def regenerateWikiPages(self, widget = None):
        dialog = gtk.Dialog(title="Generacja stron Wiki?".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.destroy_tmp)
        label = gtk.Label(("  Czy na pewno chcesz odtworzyć strony wiki?\n" +
                          "  Ta operacja może być potrzebna jeśli z jakichś przyczyn strona internetowa zawiera  \n" +
                          "  nieaktualne dane.").decode("cp1250").encode("UTF-8"))
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()

        b1 = gtk.Button("Tak")
        dialog.action_area.pack_start(b1, True, True, 3)
        b1.connect('clicked', self.regenerateWikiPagesAccept)
        b1.show()
        
        b2 = gtk.Button("Nie")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.destroy_tmp)
        b2.show()

        dialog.show()        
        return True
  

    def regenerateWikiPagesAccept(self, widget = None):
        self.config.regenerateWikiPages()
        self.destroy_tmp()


    def getMessages(self):
        if self.log_file:
            self.log_file.flush()

        reload_wiki_popup = False

        if not self.feedback_queue.empty():
            m = self.feedback_queue.get()
              
            if m == "action login ok *":
                self.w_image.set_from_file('gfx\\green.gif')
                self.wiki['state'] = "Połączony.".decode("cp1250").encode("UTF-8")
                self.all_wiki_operations_done = True
                reload_wiki_popup = True
                
            elif m == "action login fail *":
                self.w_image.set_from_file('gfx\\red.gif')
                self.wiki['state'] = str(self.wiki_proxy.last_error)
                reload_wiki_popup = True

            elif m == 'FAILED':
                print "WIKI FAILED"
                # powtarzanie operacji... dodać ###
                self.wiki_thread.ssq.put('QUIT') ### 
                self.w_image.set_from_file('gfx\\red.gif')
                self.wiki['state'] = str(self.wiki_proxy.last_error)
                reload_wiki_popup = True
                self.all_wiki_operations_done = False

            elif m == 'i quit':
                self.w_image.set_from_file('gfx\\red.gif')
                self.wiki['state'] = "Rozłączony.".decode("cp1250").encode("UTF-8")
                reload_wiki_popup = True


            elif m[:18] == "action page_save *":
                print "WIKI SAVES!", m[18:]
                if m[-3:] == 'end':
                    if self.all_wiki_operations_done:
                        print "poinformowac o wykonaniu zadania"
                        self.config.wiki_updated_queue.put(m.split('*')[1])
                    else:
                        print "awaria podczas zapisywania!"
                        self.wiki_thread.ssq.put('QUIT') ### 
                        self.w_image.set_from_file('gfx\\red.gif')
                        self.wiki['state'] = "Nieudane zapisywanie."
                        reload_wiki_popup = True
               
                elif m[-4:] != "True":
                    self.all_wiki_operations_done = False

            else:
                print "WIKI says:", m
                
            if self.wiki_popup_open and reload_wiki_popup:
                self.wiki_popup_open = False
                self.destroy_tmp()
                #self.openWikiPopUp()
        
            gobject.timeout_add(100, self.getMessages)
        else:
            gobject.timeout_add(700, self.getMessages)

    def openConfigPopUp(self, widget = None):
        dialog = gtk.Dialog(title="Konfiguracja".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect('delete_event', self.destroy_tmp)
        if not self.config_state:
            dialog.set_size_request(300, 200)
            s = "Błąd: " + self.config.last_error
            label = gtk.Label(s.decode("cp1250").encode("UTF-8"))
            dialog.vbox.pack_start(label, True, True, 5)
            label.show()

            #frame1 = gtk.Frame("Zaimportuj stary plik konfiguracyjny:".decode("cp1250").encode("UTF-8"))
            #dialog.vbox.pack_start(frame1, True, True, 5)
            #frame1.show()
            
            bNew = gtk.Button("Stwórz nowy plik.".decode("cp1250").encode("UTF-8"))
            bNew.connect('clicked', self.createNewConfigDialog)
            hbox = gtk.HBox(False, 0)
            hbox.pack_start(bNew, False, False, 10)
            hbox.show()
            dialog.vbox.pack_start(hbox, False, False, 5)
            bNew.show()

        else:
            dialog.set_size_request(300, 200)
            options = ["Adres wiki:", "Login wiki:", "Hasło wiki:"]
            visible = [ True,         True,        False ]
            keys    = ['#wiki-path', '#wiki-login','#wiki-pass']
            entries = []
            for i in range(len(options)):
                hbox = gtk.HBox(False, 0)
                label = gtk.Label(options[i].decode("cp1250").encode("UTF-8"))
                hbox.pack_start(label, True, True, 5)
                label.show()
                
                entry = gtk.Entry(max = 0)
                entry.set_visibility(visible[i])
                entry.set_editable(True)
                entry.set_text(self.config[keys[i]])
                entries.append(entry)
                hbox.pack_start(entry, True, True, 5)
                entry.show()

                dialog.vbox.pack_start(hbox, True, True, 5)
                hbox.show()
            self.new_config_values = map(lambda x,y: (x, y), keys, entries)
            
            b1 = gtk.Button("Zatwierdź".decode("cp1250").encode("UTF-8"))
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.modifyConfig)
            b1.show()
            
        b2 = gtk.Button("Cofnij")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.destroy_tmp)
        b2.show()

        dialog.show()

    def modifyConfig(self, widget = None):
        changed = False
        for key, value in self.new_config_values:
            if self.config[key] != value.get_text():
                self.config[key] = value.get_text()
                changed = True
                print key, self.config[key]

        if changed:
            self.config.sync()
            self.wikiLogout()
        self.destroy_tmp()
        self.new_config_values = None

    def createNewConfigDialog(self, widget = None):
        self.destroy_tmp()
        dialog = gtk.Dialog(title="Nowa konfiguracja".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect('delete_event', self.destroy_tmp)
        label = gtk.Label("Czy na pewno chcesz od nowa skonfigurować program?".decode("cp1250").encode("UTF-8"))
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()

        b1 = gtk.Button("Tak")
        dialog.action_area.pack_start(b1, True, True, 3)
        b1.connect('clicked', self.createNewConfig)
        b1.show()
        
        b2 = gtk.Button("Nie")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.destroy_tmp)
        b2.show()

        dialog.show()

    def createNewConfig(self, widget = None):
        self.destroy_tmp()
        self.config_state = self.config.createFile("main.db")
        if self.config_state:
            self.readConfig()
            self.c_image.set_from_file('gfx\\green.gif')
            self.openConfigPopUp()

    def wikiLogin(self):
        self.w_image.set_from_file('gfx\\yellow.gif')
        self.wiki['state'] = "Łączenie...".decode("cp1250").encode("UTF-8")
        print "WIKI LOGIN", self.config['#wiki-path'], self.config['#wiki-login'], self.config['#wiki-pass']
        self.wiki_proxy = wiki_proxy.wikiclient(self.config['#wiki-path'], self.config['#wiki-login'], self.config['#wiki-pass'])
        self.wiki_thread = wiki_thread.wikithread(self, self.wiki_proxy)
        
        self.wiki_thread.ioq.put(('login', {}))
        already_requested = []
        for key in self.config["KEYS_TO_UPDATE"]:
            if key not in already_requested:
                self.config.createWikiMessage(key)
                already_requested.append(key)
        self.config["KEYS_TO_UPDATE"] = already_requested
        self.config.sync()

        self.wiki_thread.start()

    def wikiLoginFromPopUp(self, widget = None):
        self.config.sync()
        self.wikiLogin()
        self.destroy_tmp()
        self.openWikiPopUp()

    def wikiLogout(self):
        self.wiki_thread.ssq.put('QUIT')
        self.w_image.set_from_file('gfx\\yellow.gif')
        self.wiki['state'] = "Wylogowywanie..."
        # gobject.timeout_add(30, self.getMessages)
        
    def openWikiPopUp(self, widget = None):
        if not self.config_state: return

        dialog = gtk.Dialog(title="Wiki".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        dialog.set_transient_for(self.window)
        dialog.connect('delete_event', self.destroy_tmp)
        self.tmp_dialog.append(dialog)
        s = "   Stan połączenia: \n   ".decode("cp1250").encode("UTF-8") + self.wiki['state'] + "   "
        label = gtk.Label(s)
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()

        if self.wiki['state'] not in ["Łączenie...".decode("cp1250").encode("UTF-8"),
                                      "Połączony.".decode("cp1250").encode("UTF-8"),
                                      "Wylogowywanie..."]:
            b1 = gtk.Button("Połącz".decode("cp1250").encode("UTF-8"))
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.wikiLoginFromPopUp)
            b1.show()
        #else:
        self.wiki_popup_open = True
        
        b2 = gtk.Button("Zamknij")
        dialog.action_area.pack_start(b2, True, True, 3)
        b2.connect('clicked', self.destroy_tmp)
        b2.show()

        dialog.show()
        ### problemy z label?



    #========================================================================================================
    #                               RESOURCE
    #========================================================================================================

    def testResourcesClicked(self, widget = None):
        (model, ite) = self.test_view.get_selection().get_selected()
        if ite == None:
            return
        t_id = model.get_value(ite, 0)
        if len(self.config[t_id]['items']) == 0:
            return
        self.gui_state = 'test-resource'
        i_id = self.config[t_id]['items'][0]
        self.resourcePopUp(o_id = (t_id, i_id))

    def itemResourcesClicked(self, widget = None):
        (model, ite) = self.item_view.get_selection().get_selected()
        if ite == None:
            return
        i_id = model.get_value(ite, 0)
        if self.config[i_id]['test'] == "":
            self.gui_state = 'item-resource'
            self.resourcePopUp(o_id = i_id)
        else:
            self.gui_state = 'test-resource'
            t_id = self.config[i_id]['test']
            self.resourcePopUp(o_id = (t_id, i_id))

    # ------------------------------------------------------------------------------------------------------------------------------------
    def resourcePopUp(self, widget = None, o_id = None, t_id = None):
        print o_id
        if self.gui_state == 'test-resource':
            obj = 'test'            
            id_l = self.config[o_id[0]]['items']
            chosen = id_l.index(o_id[1])
            o_id = o_id[0]
            print o_id, chosen, id_l
        else:
            obj = 'item'
            id_l = [o_id]
            chosen = 0
                    
        dialog = gtk.Dialog(title="Zasoby".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.set_size_request(750, 350)

        if obj == 'test':
            test = self.config[o_id]
            self.tracker['chosen-test'] = test
            hbox = gtk.HBox(True, 4)
            hbox.set_homogeneous(False)
            label = gtk.Label("Test: " + test['test:name'] + "   ")
            hbox.pack_start(label, False, False, 5)
            label.show()

            choose_list = []
            
            for i_id in id_l:
                item = self.config[i_id]
                choose_list.append(item['item:name'] + " [" + item['category'] + "]  (" + item['sig'] + "/...)")
                
                
            entry = gtk.Combo()
            entry.set_popdown_strings(choose_list)
            entry.entry.set_text(choose_list[chosen])
            entry.set_value_in_list(True, False)
            entry.entry.connect("changed", self.changeActiveResource)
            entry.show()
            hbox.pack_start(entry, True, True, 5)
            self.tracker['chosen-item'] = self.config[id_l[chosen]]
            print "resource:choosing", self.tracker['chosen-item']
            self.tracker['choose-list'] = choose_list

            hbox.show()
            dialog.vbox.pack_start(hbox, False, False, 5)
        else:
            item = self.config[o_id]
            label = gtk.Label(item['item:name'] + "  (" + item['sig'] + "/...)")
            dialog.vbox.pack_start(label, False, False, 5)
            label.show()
            self.tracker['chosen-item'] = item

        gui_list = []
        resource_list = []
        for i_id in id_l:
            item = self.config[i_id]
            #print item['category']
            
            if item['category'] in self.config.not_tracked_items:
                hbox = gtk.HBox(False, 5)
                hbox.set_homogeneous(False)
                s = "Dostępne:" + str(item['Q']) + " (pożądane: " + str(item['desired']) + ")"
                label = gtk.Label(s.decode("cp1250").encode("UTF-8"))
                label.show()
                hbox.pack_start(label, True, True, 5)

                adj = gtk.Adjustment(0, -9999, 9999, 1, 10)
                entry = gtk.SpinButton(adj, 1.0)
                entry.show()
                
                hbox.pack_start(entry, True, True, 5)
                button = gtk.Button(" Dodaj / usuń ".decode("cp1250").encode("UTF-8"))
                button.connect("clicked", self.updateResource)
                button.show()
                hbox.pack_start(button, False, False, 5)
                
                to_update = [label, entry]
                resource_list.append(to_update)
                gui_list.append(hbox)
                dialog.vbox.pack_start(hbox, False, False, 5)
                
            else:
                vbox = gtk.VBox(True, 5)
                vbox.set_homogeneous(False)
                
                hbox = gtk.HBox(False, 5)
                hbox.set_homogeneous(False)
                s = "Wszystkich: " + str(len(item['Q'])) + "\nDostępne: " + str(len(item['Q']) - len(item['out'])) + " (pożądane: " + str(item['desired']) + ")"
                label = gtk.Label(s.decode("cp1250").encode("UTF-8"))
                label.show()
                hbox.pack_start(label, False, False, 5)


                buttons = [(" Nowy ", self.updateResource), (" Usuń ", self.deleteElementClicked),
                           (" Zapisz opis ", self.writeDescription)]
                for b in buttons:
                    button = gtk.Button(b[0].decode("cp1250").encode("UTF-8"))
                    button.connect("clicked", b[1])
                    button.show()
                    hbox.pack_start(button, True, True, 5)
                    
                hbox.show()
                
                vbox.pack_start(hbox, False, False, 5)
                #============================================================================                
                box = gtk.HBox(True, 5)

                window = gtk.ScrolledWindow()
                store = gtk.ListStore(str, str, str)
                
                for e in item['Q']:
                    if len(e[1])> 23:
                        opis = e[1][:20] + "..."
                    else:
                        opis = e[1]
                    if len(e) > 2:
                        # id osoby wypożyczającej !
                        last = self.config[e[-1]]['pers:lname'] + ", " + self.config[e[-1]]['pers:name'] + " (do: " + e[-2] + ")"
                    else:
                        last = "dostępny".decode("cp1250").encode("UTF-8")
                    store.append([e[0], opis.replace("\n", " "), last])
                
                view = gtk.TreeView(store)
                names = ["Sygnatura", "Opis", "Stan"]
                for i in range(3):
                    column = gtk.TreeViewColumn(names[i].decode("cp1250").encode("UTF-8"))
                    view.append_column(column)
                    cell = gtk.CellRendererText()
                    column.pack_start(cell, True) # True = expand
                    column.add_attribute(cell, 'text', i)

                view.show()
                view.connect("cursor-changed", self.displayDescription)
                window.add(view)
                selection = view.get_selection()
                selection.set_mode(gtk.SELECTION_BROWSE)
                
                window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                window.set_shadow_type(gtk.SHADOW_IN)
                window.show()

                
                box.pack_start(window, True, True, 5)
                
                #==============================================================================
                              

                window = gtk.ScrolledWindow()

                entry = gtk.TextView()
                entry.set_editable(True)

                default = ""
                
                entry.get_buffer().set_text(default)
                entry.set_wrap_mode(gtk.WRAP_WORD)

                window.add(entry)
                window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                window.set_shadow_type(gtk.SHADOW_IN)
                entry.show()
                window.show()
                box.pack_start(window, True, True, 5)
                box.show()
                
                vbox.pack_start(box, True, True, 2)
                gui_list.append(vbox)
                
                #==============================================================================
                to_update = [label, store, view, entry]
                resource_list.append(to_update)
                dialog.vbox.pack_start(vbox, True, True, 5)
                
                

        gui_list[chosen].show()
        self.gui_list = gui_list
        self.resource_list = resource_list
        self.tracker['resource-idx'] = chosen
        self.tracker['last-element'] = None

        modes = [("Koniec", self.abort)]
        
        for m in modes:
            button = gtk.Button(m[0].decode("cp1250").encode("UTF-8"))
            button.connect("clicked", m[1])
            button.show()
            dialog.action_area.pack_start(button, True, True, 3)

        dialog.connect("delete_event", self.abort)
        dialog.show()

    def displayDescription(self, widget = None):
        self.writeDescription()
        
        item = self.tracker['chosen-item']
        index = self.tracker['resource-idx']        
        (model, ite) = self.resource_list[index][2].get_selection().get_selected()
        if ite == None:
            e = self.resource_list[index][3].get_buffer()
            e.set_text("")
        self.tracker['last-element'] = ite
        sig = model.get_value(ite, 0)
        for i in range(len(item['Q'])):
            if item['Q'][i][0] == sig:
                idx = i
                break
        e = self.resource_list[index][3].get_buffer()
        e.set_text(item['Q'][idx][1])

    def writeDescription(self, widget = None):
        item = self.tracker['chosen-item']
        if item['category'] in self.config.not_tracked_items:
            return
        if self.tracker['last-element'] == None:
            return
        ite = self.tracker['last-element']
        
        index = self.tracker['resource-idx']
        model = self.resource_list[index][1]
        sig = model.get_value(ite, 0)

        for i in range(len(item['Q'])):
            if item['Q'][i][0] == sig:
                idx = i
                break
        e = self.resource_list[index][3].get_buffer()
        item['Q'][idx][1] = e.get_text(e.get_start_iter(), e.get_end_iter())
        self.config[item['ID']] = item
        self.config.sync()
        if len(item['Q'][idx][1])> 23:
            opis = item['Q'][idx][1][:20] + "..."
        else:
            opis = item['Q'][idx][1]
        model.set_value(ite, 1, opis.replace("\n", " "))
        print item['Q'][idx]


    def changeActiveResource(self, widget = None):
        self.writeDescription()
        self.tracker['last-element'] = None
        entry = widget.get_text()
        index = self.tracker['choose-list'].index(entry)
        print index
        self.tracker['resource-idx'] = index
        for g in self.gui_list:
            g.hide()
        self.gui_list[index].show()
        self.tracker['chosen-item'] = self.config[self.tracker['chosen-test']['items'][index]]

    def deleteElementClicked(self, widget = None):
        ### dodać potwierdzenie
        item = self.tracker['chosen-item']
        index = self.tracker['resource-idx']  
        (model, ite) = self.resource_list[index][2].get_selection().get_selected()
        if ite == None:
            return

        self.gui_state += "?rdelete"
        print self.gui_state
        
        sig = model.get_value(ite, 0)

        dialog = gtk.Dialog(title="Usuwanie egzemplarza.".decode("cp1250").encode("UTF-8"),
                            parent=self.window, flags=gtk.DIALOG_MODAL  | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=None)
        self.tmp_dialog.append(dialog)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)

        
        if model.get_value(ite, 2) != "dostępny".decode("cp1250").encode("UTF-8"):
            label = gtk.Label("Nie można usunąć wypożyczonego egzemplarza.\n".decode("cp1250").encode("UTF-8"))
            isOK = False
        else:
            label = gtk.Label("Czy na pewno chcesz usunąć egzemplarz:\n".decode("cp1250").encode("UTF-8") + sig)
            isOK = True
        dialog.vbox.pack_start(label, True, True, 20)
        label.show()


        if isOK:
            b1 = gtk.Button("Tak")
            dialog.action_area.pack_start(b1, True, True, 3)
            b1.connect('clicked', self.deleteElementApproved)
            b1.show()

            b2 = gtk.Button("Nie")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()
        else:
            b2 = gtk.Button("OK")
            dialog.action_area.pack_start(b2, True, True, 3)
            b2.connect('clicked', self.abort)
            b2.show()            

        dialog.show()        
        return True

    def deleteElementApproved(self, widget = None):
        ### dodać potwierdzenie
        item = self.tracker['chosen-item']
        index = self.tracker['resource-idx']        
        (model, ite) = self.resource_list[index][2].get_selection().get_selected()
        if ite == None:
            return
        sig = model.get_value(ite, 0)
        el = item['Q']
        item['history'].append( [sig, "usunięty".decode("cp1250").encode("UTF-8"), self.time2string(time.time()), ""] )
        
        for i in range(len(item['Q'])):
            if item['Q'][i][0] == sig:
                idx = i
                break

        item['Q'].pop(i)
        self.config[item['ID']] = item
        self.config.sync()
        self.resource_list[index][1].remove(ite)
        s = "Wszystkich: " + str(len(item['Q'])) + "\nDostępne: " + str(len(item['Q']) - len(item['out'])) + " (pożądane: " + str(item['desired']) + ")"
        self.resource_list[index][0].set_text(s.decode("cp1250").encode("UTF-8"))
        
        if item['test'] != "":
            self.updateTestRow(item['test'])

        self.updateItemRow(item['ID'])
        self.tracker['last-element'] = None
        e = self.resource_list[index][3].get_buffer()
        e.set_text("")
        self.abort()
           

    def updateResource(self, widget = None):
        item = self.tracker['chosen-item']
        index = self.tracker['resource-idx']
        if item['category'] in self.config.not_tracked_items:
            value = self.resource_list[index][1].get_value_as_int()
            item['Q'] += value
            item['history'].append([item['sig'], 'dodane w liczbie ' + str(value), self.time2string(time.time()), ""])
            self.config[item['ID']] = item
            self.config.sync()
            self.resource_list[index][1].set_value(0)
            s = "Dostępne: " + str(item['Q']) + " (pożądane: " + str(item['desired']) + ")"
            self.resource_list[index][0].set_text(s.decode("cp1250").encode("UTF-8"))
        else:
            item['last-sig'] += 1
            item['Q'].append([item['sig'] +"/"+ str(item['last-sig']), ""])
            item['history'].append([item['sig'] +"/"+ str(item['last-sig']), 'dodany', self.time2string(time.time()), ""])
            print item['Q']
            self.resource_list[index][1].append(item['Q'][-1] + ["dostępny".decode("cp1250").encode("UTF-8")])
            self.config[item['ID']] = item
            self.config.sync()            
            s = "Wszystkich: " + str(len(item['Q'])) + "\nDostępne: " + str(len(item['Q']) - len(item['out'])) + " (pożądane: " + str(item['desired']) + ")"
            self.resource_list[index][0].set_text(s.decode("cp1250").encode("UTF-8"))
            
            
        if item['test'] != "":
            self.updateTestRow(item['test'])

        self.updateItemRow(item['ID'])



    def printDebtorListClicked(self, widget = None):
        """
        Naciśnięcie przycisku drukowania dłużników. Otwiera okno wyboru pliku.
        """
        if not self.check_gui_transition('dept-export'):
            print "abnormal gui transition! '" + str(self.gui_state) + "' to 'dept-export'"
            return
        self.gui_state = 'dept-export'
        print self.gui_state

        dialog = gtk.FileSelection("Wybierz gdzie zapisać plik".decode("cp1250").encode("UTF-8"))
        dialog.set_modal(True)
        dialog.set_transient_for(self.window)
        dialog.connect("delete_event", self.abort)
        self.tmp_dialog.append(dialog)
        dialog.ok_button.connect('clicked', self.printDebtorList)
        dialog.cancel_button.connect('clicked', self.abort)
        dialog.complete("zaleglosci.txt")
        dialog.hide_fileop_buttons()
        dialog.set_select_multiple(False)
        dialog.show()


    def printDebtorList(self, widget = None):
        """
        Drukowanie listy dłużników do pliku. Kodowanie cp1250.
        """

        # pobieranie danych
        data_str = self.time2string(time.time())
        print_list = []
        for p_id in self.config['#PERS_LIST']:
            person = self.config[p_id]
            if person['rent_date'] and person['rent_date'] < data_str:
                tmp = []
                for key in ["pers:lname", "pers:name", "rent_date"]:
                    tmp.append(person[key])
                print_list.append(" ".join(tmp))
        
        # drukowanie do pliku
        dialog = self.tmp_dialog[-1]
        file_name = dialog.get_filename()
        try:
            # może sprawdzać czy nie nadpisuje? :P.. zamiana na UTF jest niebezpieczna, lepiej zapisać jako HTML w utf-8
            dept_file = open(file_name, 'w')
            dept_file.write("\n".join(print_list).decode("UTF-8").encode("cp1250"))
            dept_file.close()
        except Exception, e:
            print e
            return
        self.abort()


def personVisibility(model, iter, data = None):
    if data.dummy_filtering: return True
    for i in range(len(data.personChoosingFields)):
        #print data.personChoosingFields, model.get_value(iter, 0), data.personChoosingFields[i][2]
        #print model.get_value(iter, 1)
        if not data.personChoosingFields[i][3] in model.get_value(iter, data.personChoosingFields[i][2]):
            return False
    
    return True

def itemVisibility(model, iter, data = None):
    if data.dummy_filtering: return True
    for i in range(len(data.itemChoosingFields)):
        #print data.personChoosingFields, model.get_value(iter, 0), data.personChoosingFields[i][2]
        #print model.get_value(iter, 1)
        pattern = data.itemChoosingFields[i][3].lower()
        if not pattern in model.get_value(iter, data.itemChoosingFields[i][2]).lower():
            return False
    
    return True  
