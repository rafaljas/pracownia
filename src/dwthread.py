# -*- coding: cp1250 -*-
# created: 2007-12-06 11:35:35
# modified: 2008-01-23 12:53:44
# filename: dwthread

# place for file global imports and defines
import dwclient as dokuwiki
import threading, time, Queue
import re
import logging

logger = logging.getLogger("pracownia")

# some place for code
class wikithread(threading.Thread):
	def __init__(self, parent, wikiclient):
		threading.Thread.__init__(self)
		self.ssq = Queue.Queue()
		self.ioq = Queue.Queue()
		self.parent = parent
		self.wiki = wikiclient
		self.alive = True
		self.err_counter = 0
		self.__MAX_ERROR = 3

	# method representing the thread's activity, system-status-queue handling
	def run(self):
		ss_msg = 'START' # per default start thread
		while True: # endless loop chains
			if not self.ssq.empty():
				ss_msg = self.ssq.get() # to check, non blocking
				#print '%%% ss_msg', ss_msg

			if ss_msg == 'START':
				self.alive = True
				self.parent.feedback_queue.put('started')
			if ss_msg == 'STOP':
				self.alive = False
				self.parent.feedback_queue.put('stopped')
			if ss_msg == 'QUIT':
				break

			ss_msg = "" # do not report feedback in next iteration

			if self.alive:
				self.handle_ioq()

		# in unchained turn off, report it, then quit
		self.alive = False
		self.parent.feedback_queue.put('i quit')
	
	# input-ouput-queue handler
	def handle_ioq(self):
		if self.ioq.empty():
			time.sleep(1)
			return
				
		io_msg = self.ioq.get()
				
		if not (isinstance(io_msg, tuple) or isinstance(io_msg, list)):
			self.parent.feedback_queue.put('input queue data dropped * type error')
			return
				
		if len(io_msg) is not 2:
			self.parent.feedback_queue.put('input queue data dropped * wrong number of parameters')
			return

		action = io_msg[0]
		datadict = io_msg[1]

		if not isinstance(action, str) or action not in ['page_get', 'page_save', 'page_del', 'login', 'logout']:
			self.parent.feedback_queue.put('input queue data dropped * unknown action')
			return

		if not isinstance(datadict, dict):
			self.parent.feedback_queue.put('input queue data dropped * unknown action')
			return

		self.err_counter = 0
		while self.err_counter < self.__MAX_ERROR:
			try:
				self.handle_action(action, datadict)
				return
			except Exception, e:
				#print "wyjątek", e # debug
				self.err_counter += 1
				self.parent.feedback_queue.put('FAILED')

	# actions handler
	def handle_action(self, action, datadict):
		# sprawdzanie czy aktualizacja czy dodanie nowej strony
		# jesli to jest aktulazizacja to spr. czy nie zmieniła sie grupa
		#dd['id'] = id_system.replace(':', '-system:', 1)
		dd = {}
		for key in datadict.keys():
			dd[key.lower()] = datadict[key]

		#print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"

		if action == 'page_get':
			if not 'id' in dd.keys():
				self.parent.feedback_queue.put('action page_get dropped * no ID given')
				return
			if 'rev' in dd.keys():
				page_html = self.wiki.page_get(dd['id'], dd['rev'])
			else:
				page_html = self.wiki.page_get(dd['id'])
			self.parent.feedback_queue.put(page_html)

		if action == 'page_get_txt':
			if not 'id' in dd.keys():
				self.parent.feedback_queue.put('action page_get_txt dropped * no ID given')
				return
			if 'rev' in dd.keys():
				page_txt = self.wiki.page_get_txt(dd['id'], dd['rev'])
			else:
				page_txt = self.wiki.page_get_txt(dd['id'])
			self.parent.feedback_queue.put(page_txt)

		if action == 'page_save':
			# page id required
			if not 'id' in dd.keys():
				self.parent.feedback_queue.put('action page_save dropped * no ID given')
				return

			logger.info('WIKI: saving... {}'.format(dd['id']))
			# save group
			if dd['id'][:5] == 'group':
				#print datadict
				content = ""
				groups = datadict.keys()
				groups.remove('id')
				groups.remove('Inne')
				groups.sort()
				groups.append('Inne')
				test_list = [content]
				##print groups

				for group in groups:
					content = "\n\n==== %s ====\n\n" % group
					test_list.append(content)
					pairs = datadict[group]
					pairs.sort(lambda x, y: cmp(x[1], y[1]))
					for test_pair in pairs:
						link = 'test' + test_pair[0][5:]					
						# unwikify...
						test_list.append("  * [[testy:%s|%s]]\n" % (link, test_pair[1]))
					test_list.append('\n')
				content = "".join(test_list)
				#print content

				page_save_status = self.wiki.page_save('testy:start', content)
				self.parent.feedback_queue.put('action page_save * ' + dd['id'] + ' ' + str(page_save_status))
                                self.parent.feedback_queue.put('action page_save * ' + dd['id'] + ' end')
				return True

			# save group
			if dd['id'] == 'category':
				#print datadict
				content = ""
				groups = datadict.keys()
				groups.remove('id')
				groups.sort()
				test_list = [content]
				#print groups

				for group in groups:
					content = "\n\n==== %s ====\n\n" % group
					test_list.append(content)
					pairs = datadict[group]
					pairs.sort(lambda x, y: cmp(x[1], y[1]))
					for test_pair in pairs:
						link = 'item' + test_pair[0][5:]					
						# unwikify...
						test_list.append("  * [[przedmioty:%s|%s]]\n" % (link, test_pair[1]))
					test_list.append('\n')
				content = "".join(test_list)
				#print content

				page_save_status = self.wiki.page_save('przedmioty:start', content)
				self.parent.feedback_queue.put('action page_save * ' + dd['id'] + ' ' + str(page_save_status))
                                self.parent.feedback_queue.put('action page_save * ' + dd['id'] + ' end')
				return True

			# {{{ data processing to user friendly format
			od, ld = {}, {}
			unw_keys = ['test:name', 'test:public', 'author', 'publisher', 'group',	'item:name', 'item:public', 'category']
			uncc_keys = ['id', 'author', 'group']
			for key in dd.keys():
				token = dd[key]
				if key in unw_keys:
					token = self.unwikify(token)
					od[key] = token
				if key in uncc_keys:
					token = self.uncustomchar(token)
					ld[key] = token
			# }}}

			# save item
			if ld['id'][:4] == 'item':
				item_id = 'przedmioty:' + ld['id']
				item_list_id = 'przedmioty:start'

				# update test
				test_content = '====== %s ======\n' % (od['item:name']) # make title
				test_content += '|  Autor:|%s  |\n|  Wydawca:|%s  |\n|  Kategoria:|%s  |\n\n' % (od['author'], od['publisher'], od['category'])
				test_content += "| Dostęne:|".decode("cp1250").encode("UTF-8")
				if isinstance(datadict['Q'], int):
					test_content += str(datadict['Q']) + " |\n\n"
				else:
					test_content += str(len(datadict['Q']) - len(datadict['out'])) + " z " + str(len(datadict['Q'])) + " |\n\n"
				test_content += od['item:public'] # add page content

				page_save_status = self.wiki.page_save(item_id, test_content)
				self.parent.feedback_queue.put('action page_save * ' + item_id + ' ' + str(page_save_status))
                                self.parent.feedback_queue.put('action page_save * ' + ld['id'] + ' end')
				return True
		
			# save test
			if ld['id'][:4] == 'test':
				# have all pages id available

				test_id = 'testy:' + ld['id']
				test_list_id = 'testy:start'

				# update test
				test_content = '====== %s ======\n' % (od['test:name']) # make title
				test_content += '|  Autor:|%s  |\n|  Wydawca:|%s  |\n|  Grupa:|%s  |\n\n' % (od['author'], od['publisher'], od['group'])
				test_content += "Test zawiera:\n"
				for item in datadict['items']:
					test_content += item['item:name'] + " ( dostępne: ".decode("cp1250").encode("UTF-8")
					if isinstance(item['Q'], int):
						test_content += str(item['Q']) + " )\n"
					else:
						test_content += str(len(item['Q']) - len(item['out'])) + " )\n"
				test_content += "\n"
				test_content += od['test:public'] # add page content

				page_save_status = self.wiki.page_save(test_id, test_content)
				self.parent.feedback_queue.put('action page_save * ' + test_id + ' ' + str(page_save_status))
                                self.parent.feedback_queue.put('action page_save * ' + ld['id'] + ' end')
				return True

		if action == 'page_del':
			if not 'id' in dd.keys():
				self.parent.feedback_queue.put('action page_del dropped * no ID given')
				return

			page_id = dd['id'].split('#')
			if 'ITEM' == page_id[0]:
				page_id = 'przedmioty:item' + page_id[1]
			if 'TEST' == page_id[0]:
				page_id = 'testy:test' + page_id[1]
			
			#print page_id
			page_del_status = self.wiki.page_del(page_id)
			if page_del_status:
				self.parent.feedback_queue.put('action page_del ok * True')
			else:
				self.parent.feedback_queue.put('action page_del fail * False')

		if action == 'login':
			self.wiki.log_in()
			if self.wiki.is_loggedin():
				self.parent.feedback_queue.put('action login ok *')
			else:
				self.parent.feedback_queue.put('action login fail *') # TODO: powód

		if action == 'logout':
			self.wiki.log_out()
			if not self.wiki.is_loggedin():
				self.parent.feedback_queue.put('action logout ok *')
			else:
				self.parent.feedback_queue.put('action logout fail *') # TODO: powód

		return True
	
	# clean data from all characters except letters
	def uncustomchar(self, input):
		output = input
		customchar_filters = [
				# accept only letters
				('\W', '')
				]

		for filter in customchar_filters:
			pattern = filter[0]
			replstr = filter[1]
			output = re.sub(pattern, replstr, output)

		return output.lower()

	# clean data from possible dokuwiki formating strings
	def unwikify(self, wiki_content):
		raw_content = wiki_content
		wiki_filters = [
				# at begining remove emoticons
				('8-\)', ''),
				('8-O', ''),
				(':-\(', ''),
				(':-\)', ''),
				('=\)', ''),
				(':-/', ''),
				(':-\\\\', ''),
				(':-\?', ''),
				(':-D', ''),
				(':-P', ''),
				(':-O', ''),
				(':-X', ''),
				(':-\|', ''),
				(';-\)', ''),
				('\^_\^', ''),
				(':\?:', ''),
				(':\!:', ''),
				('LOL', ''),
				('FIXME', ''),
				('DELETEME', ''),
				# replace 2 spaces or more to space
				('\ {2,}', ' '),
				# replace ==, ===, ====, =====, ====== to =
				('={2,6}', '='),
				# replace <del> </del> to empty string
				('<del>', ''),
				('</del>', ''),
				# replace <>()[]{} to ::
				('[<\[\{]', '('),
				# replace <>()[]{} to ::
				('[>\]\}]', ')'),
				# replace any of * / - _ ' to empty string
				#('[_/\-]+', ''),
				# replace * to *
				('\*{2,}', '*'),
				('\*', '<html>&#8727;</html>'),
				# replace | to /
				('\|', '/'),
				# replace tabs to spaces
				('\t', ' '),
				# replace every new line to double new line
				('\n', '\n\n'),
				]

		for filter in wiki_filters:
			pattern = filter[0]
			replstr = filter[1]
			raw_content = re.sub(pattern, replstr, raw_content)

		return raw_content




#{{{ python version check
if __name__ == '__main__':
		from sys import version_info, exit, stderr

		ver = (2,5)
		if ver > version_info[:2]:
				stderr.write("Python is too old, please clean up the molt and rejuvenate to version %d.%d.\n" % ver)
				exit(1)
		#}}}

