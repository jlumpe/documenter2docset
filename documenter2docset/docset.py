"""Generate Dash docsets."""

import os
from pathlib import Path
import sqlite3

import plistlib


def init_sqlite_index(conn):
	"""Initialize the SQLite index database."""
	cur = conn.cursor()

	try:
		cur.execute('DROP TABLE searchIndex;')
	except:
		pass

	cur.execute('CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
	cur.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);')

	conn.commit()


def add_index_item(cur, name, type_, path):
	cur.execute('INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)', (name, type_, path))


class DocSet:

	def __init__(self, path):
		self.path = Path(path)

	index_path = property(lambda self: self.path / 'Contents/Resources/docSet.dsidx')
	info_path = property(lambda self: self.path / 'Contents/Info.plist')
	docs_path = property(lambda self: self.path / 'Contents/Resources/Documents')

	def connect_index(self):
		"""Get a connection to the index database."""
		return sqlite3.connect(str(self.index_path))

	def read_info(self):
		with open(self.info_path) as fh:
			return plistlib.load(fh, fmt=plistlib.FMT_XML)

	def write_info(self, info):
		with open(self.info_path, 'wb') as  fh:
			return plistlib.dump(info, fh, fmt=plistlib.FMT_XML)

	def add_index_items(self, items):
		conn = self.connect_index()
		cur = conn.cursor()

		for item in items:
			add_index_item(cur, *item)

		conn.close()

	@classmethod
	def init(cls, path):
		"""Initialize a new docset directory.

		Parameters
		----------
		path
			Root directory.

		Returns
		-------
		.DocSet
		"""

		docset = cls(path)

		# Initialize directory structure
		docset.path.mkdir()
		os.makedirs(docset.docs_path)

		# Create info.plist file
		docset.write_info({})

		# Initialize database
		conn = docset.connect_index()
		init_sqlite_index(conn)
		conn.close()

		return docset
