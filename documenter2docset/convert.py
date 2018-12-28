"""Convert Documenter.jl documentation data to Dash docset."""

import os
import shutil
from pathlib import Path
import logging

from .documenter import read_search_index
from .docset import DocSet, add_index_item


# Maps "category" property in item from Documenter.jl's search_index.js to
# value of "type" column in Dash index db table.
CATEGORY_TO_TYPE = {
	'page': 'Guide',  # Seems like the most appropriate
	'section': 'Section',
	'function': 'Function',
}


CONFIG_TEMPLATE = '''\
{{
	"name": "{name}",
	"id": "{id}",
	"index":  "index.html",
	"fallbackUrl": null,
	"enableJavascript": false
}}'''


def make_init_config(name, id=None):
	"""Make an initial configuration file."""
	if id is None:
		id = name.lower()

	return CONFIG_TEMPLATE.format(name=name, id=id)


def documenter2docset(src, name, dest, **kwargs):
	converter = Converter(**kwargs)
	converter.convert(src, name, dest)


class Config:

	def __init__(self, name, **kwargs):
		self.name = name
		self.id = kwargs.get('id', self.name.lower())
		self.index = kwargs.get('index', None)
		self.fallback_url = kwargs.get('fallbackUrl', None)
		self.enable_javascript = kwargs.get('enableJavascript', False)

	@classmethod
	def from_json(cls, data):
		data = dict(data)

		try:
			name = data.pop('name')
		except KeyError:
			raise KeyError('Config requires a "name" key.') from None

		return cls(name, **data)


class Converter:

	def __init__(self):
		self.logger = logging.getLogger(__name__)

	def convert(self, src, config, dest):

		src = Path(src)
		dest = Path(dest)

		self.logger.info('Creating output directory...')
		docset = DocSet.init(dest)

		# Write info.plist
		self.logger.info('Writing info.plist ...')
		info = self.make_info(config)
		self.logger.debug(info)
		docset.write_info(info)

		# Convert search index
		self.logger.info('Reading search_index.js ...')
		with open(src / 'search_index.js') as fh:
			index = read_search_index(fh)

		self.logger.info('Writing search index to docset ...')
		self.write_search_index(index, docset)

		# Convert source files
		self.logger.info('Converting source files...')
		for file in self.find_src_files(src):
			destfile = docset.docs_path / file
			destfile.parent.mkdir(parents=True, exist_ok=True)
			self.convert_src_file(src / file, destfile)

		# Copy assets
		self.logger.info('Copying assets...')
		shutil.copytree(src / 'assets', docset.docs_path / 'assets')

	def make_info(self, config):
		"""Make info.plist data from config."""
		info = {
			'CFBundleIdentifier': config.id,
			'CFBundleName': config.name,
			'DocSetPlatformFamily': config.id,
			'isDashDocset': True,
		}

		if config.index is not None:
			info['dashIndexFilePath'] = config.index

		if config.fallback_url is not None:
			info['DashDocSetFallbackURL'] = config.fallback_url

		if config.enable_javascript:
			info['isJavaScriptEnabled'] = True

		return info

	def convert_index_item(self, item):
		"""Processes an item from search_index.js to a Dash SQLite index row.

		Returns
		-------
		tuple
			``(name, type, path)`` tuple.
		"""
		type_ = CATEGORY_TO_TYPE[item['category']]
		return (item['title'], type_, item['location'])

	def write_search_index(self, index, docset):
		conn = docset.connect_index()
		cur = conn.cursor()

		for item in index:
			try:
				converted = self.convert_index_item(item)
			except Exception as exc:
				self.logger.warning("Couldn't convert search index item %s: %s", item['title'], exc)
				continue

			add_index_item(cur, *converted)

		conn.commit()
		conn.close()

	def find_src_files(self, root):
		for dirpath, dirnames, filenames in os.walk(root):
			rel = Path(dirpath).relative_to(root)
			for file in filenames:
				if os.path.splitext(file)[1] == '.html':
					yield rel / file

	def convert_src_file(self, src, dest):
		self.logger.debug('%s -> %s', src, dest)
		shutil.copy(src, dest)
