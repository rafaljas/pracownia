# -*- coding: iso-8859-2 -*-
#
# (c) Rafał Jasicki 2007
# Uniwersytet Wrocławski / praca magisterska

"""termdb dla systemu bibliotecznego"""

__version__ = '0.02'
__author__ = 'Rafał Jasicki'

# public API
__all__ = []

# some place for code

class termdb:
	def __init__(self, l_path, s_period = 10):
		assert isinstance(l_path, str)
		assert isinstance(s_period, int) and s_period > 0
		self.__tdb_path = l_path
		self.__tdb = bsddb.hashopen(self.__tdb_path, "c") # read/write mode
		self.__tdb_sync_period = s_period
		self.__tdb_query_counter = 0
	
	def __sync(self):
		self.__tdb_query_counter += 1
		if self.__tdb_query_counter > self.__tdb_sync_period:
			self.__tdb.sync()
			print 'syncing'
			self.__tdb_query_counter = 0

	# emulate list methods
	def __len__(self):
		return len(self.__tdb)

	def __getitem__(self, key):
		serial_item = self.__tdb[key]
		deserial_item = pickle.loads(serial_item)
		return deserial_item
	
	def __setitem__(self, key, value):
		deserial_item = value
		serial_item = pickle.dumps(deserial_item, 2)
		self.__tdb[key] = serial_item
		#self.__sync()

	def __delitem__(self, key):
		del self.__tdb[key]
		#self.__sync()

	def __contains__(self, key):
		return (key in self.__tdb)

	# db methods
	def keys(self):
		return self.__tdb.keys()

	def sync(self):
		return self.__tdb.sync()
	
	def clear(self):
		for key in self.__tdb.keys():
			del self.__tdb[key]
	
	def append(self, key, value):
		left_item = self.__tdb[key]
		right_item = value
		deserial_item = left_item.extend(right_item)
		serial_item = pickle.dumps(deserial_item, 2)
		self.__tdb[key] = serial_item
		self.__sync()


# main entry point handler
if __name__ == '__main__':
	from sys import version_info, exit, stderr

	ver = (2,4)
	if ver > version_info[:2]:
		stderr.write("Python is too old, please clean up the molt and rejuvenate to version %d.%d.\n" % ver)
		exit(1)
	
	stderr.write("This file is a part of kdGoo. Get full version or leave me alone!\n")
else:
	import bsddb
	import cPickle as pickle
	#import pickle as pickle
