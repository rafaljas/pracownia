# coding: cp1250
# Rafal Jasicki




def main(nf, args):
    import pygtk
    import gtk
    import gobject
    from sys import path
    
    path.append("." + sep + "src")
    import main_window
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    mw = main_window.MainWindow(nf)
    mw.main()

    gtk.gdk.threads_leave()
    #print path
    


def checkIfFree():
    
    dir_path = os.path.abspath("." + sep + "data" + sep)
    g = glob.glob("." + sep + "data" + sep + "*.lock")
    if not g:
        lock = tempfile.NamedTemporaryFile('w+b', -1, ".lock", "blokada", dir_path)
        #time.sleep(1)
        g = glob.glob("." + sep + "data" + sep + "*.lock")
        for p in g:
            if not lock.name[1:] in p:
                print "lock to be deleted:", p
                os.remove(p)
    else:
        for p in g:
            #print "lock:", p
            os.remove(p)
        lock = tempfile.NamedTemporaryFile('w+b', -1, ".lock", "blokada", dir_path)
    # print lock.name
    return lock


def setup_logger():
    l = logging.getLogger("pracownia")
    h = logging.handlers.RotatingFileHandler("data" + sep + "log.txt", mode='a', maxBytes=600000, backupCount=6, encoding=None, delay=0)
    h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    l.addHandler(h)
    l.setLevel(1)
    return l

if __name__ == '__main__':
    import time, sys
    from sys import argv
    from os import sep
    import os
    import tempfile, glob
    import logging
    import logging.handlers

    logger = setup_logger()
    cont = False

    logger.info("checking LOCK")

    lock = checkIfFree()

    if not lock:
            sys.exit(1)
    logger.info("free to go!")
    nf = open('logfile', 'w+')
    sys.stdout = nf
    sys.stdout = sys.__stdout__
    logger.info("lock OK")
    nf.close()
    # logger = False
    # logger = True
    nf = False

    if logger:
        file_path = "." + sep + "data" + sep + 'logfile'
        try:
            if os.stat(file_path).st_size > 600000:
                try:
                    os.remove(file_path + ".old")
                except:
                    print "no file to remove"
                os.rename(file_path, file_path + ".old")
                nf = open(file_path, 'w')
                print "moved"
            else:
                nf = open(file_path, 'a+')
        except:
            nf = open(file_path, 'a+')
        sys.stdout = nf
        sys.stderr = nf
    
    main(nf, argv)
    if logger:
        sys.stdout = sys.__stdout__
        nf.close()
    logger.info("STOP")
    lock.close()


