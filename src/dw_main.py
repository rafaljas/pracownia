# -*- coding: cp1250 -*-
# created: 2007-11-26 11:03:47
# filename: dwp_main

# place for file global imports and defines
import dwclient as dokuwiki
import dwthread as wikithread
import Queue

import time

# some place for code
class app:
	def __init__(self):
		self.feedback_queue = Queue.Queue()
		self.wiki_client = dokuwiki.wikiclient('http://localhost/dw/', 'user', 'user')

		self.wiki_thread = wikithread.wikithread(self, self.wiki_client)
		#self.wiki_thread = wikithread.WikiThread(self)
		#self.wiki_thread.setProxy(self.wiki_client)

		self.wiki_thread.start()
	

	def go(self):
		while True:
			print 'saving'
			self.wiki_thread.ioq.put(['page_save', {'id': 'TEST:#10101', 'c': '''asdf'''}])
			print 'saved'
			time.sleep(2)
			break

		self.wiki_thread.ssq.put('QUIT')


def main():
	application = app()
	application.go()

def main2():
	wiki_client = dokuwiki.wikiclient('http://localhost/dw/', 'user', 'user')

	#print wiki_client.page_get('start')

	#print wiki_client.page_get()
	#print wiki_client.is_loggedin()
	#wiki_client.log_in()
	#print wiki_client.is_loggedin()
	#wiki_client.log_out()
	#print wiki_client.is_loggedin()
	pc = 'sprawdzanie zawartosci strony\ndrugia linijka\n   3 spacje w 3ciejlinijce\n\n'
	print wiki_client.page_save('wiki:savetest', pc)
	#print wiki_client.page_del('piaskownica:savetest')
	

#{{{ python version check
if __name__ == '__main__':
	from sys import version_info, exit, stderr

	ver = (2,5)
	if ver > version_info[:2]:
		stderr.write("Python is too old, please clean up the molt and rejuvenate to version %d.%d.\n" % ver)
		exit(1)
	#}}}

	main()

