"""Command line interface."""

import os
import sys
import shutil
import argparse
import json
import logging

from .convert import documenter2docset, make_init_config, Config


DESC = '''
Convert Julia package documentation generated with Documenter.jl to a Dash-compatible
docset.
'''
DESC = ' '.join(DESC.strip().splitlines())


parser = argparse.ArgumentParser(description=DESC)
subparsers = parser.add_subparsers(dest='cmd')
parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity level')
parser.add_argument('-c', '--config', help='Path to config file', default='docset.json')


init_parser = subparsers.add_parser('init', help='Initialize project with a new config file.')
init_parser.add_argument('name', nargs='?', help='Name of project')
init_parser.add_argument('-f', '--force', action='store_true',
                         help='Overwrite existing config file')


build_parser = subparsers.add_parser('build', help='Build a doc set.')

build_parser.add_argument('path', help='Path to Documenter.jl build directory')

build_parser.add_argument('-o', dest='dest', help='Path to write docset to')

build_parser.add_argument('-f', '--force', action='store_true',
                    help='Overwrite output directory if it exists')



def main(argv=None):
	if argv is None:
		argv = sys.argv[1:]

	args = parser.parse_args(argv)

	if args.verbose >= 2:
		loglevel = logging.DEBUG
	elif args.verbose == 1:
		loglevel = logging.INFO
	else:
		loglevel = logging.WARN

	logging.basicConfig(level=loglevel, format='%(levelname)s: %(message)s')

	if args.cmd == 'init':
		init(args)
	elif args.cmd == 'build':
		build(args)
	else:
		parser.print_help()


def init(args):

	# Handle destination path already exists
	if os.path.exists(args.config):
		if args.force:
			os.remove(args.config)
		else:
			print('Refusing to overwrite %s without --force' % args.config)
			sys.exit(1)

	name = args.name or 'MyProject'

	with open(args.config, 'w') as fh:
		fh.write(make_init_config(name))

	print('Edit %s and then run "%s build"' % (args.config, os.path.basename(sys.argv[0])))


def build(args):

	with open(args.config) as fh:
		config = Config.from_json(json.load(fh))

	dest = args.dest
	if dest is None:
		dest = config.id + '.docset'

	# Handle destination path already exists
	if os.path.exists(dest):
		if args.force:
			shutil.rmtree(dest)
		else:
			print('Refusing to overwrite %s without --force' % dest)
			sys.exit(1)

	documenter2docset(args.path, config, dest)


if __name__ == '__main__':
	main()
