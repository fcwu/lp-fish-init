#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright (C) 2013 Doro Wu <doro.wu@canonical.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

from command import CommandBase
import sys
import logging
import subprocess
from settings import Settings
import os
from shellcommand import ShellCommand
#from lp_fish_tools.BzrProject import sourceBranch, ubuntuRelease


class Command(CommandBase):
    def create(self):
        filename = 'manifest.html'
        while os.path.exists(filename):
            msg = ('Found {}.'
                   ' Overwrite? [y]es/[n]o/[r]ename]> ').format(filename)
            inp = raw_input(msg).lower()
            if inp == "y":
                os.remove(filename)
                break
            elif inp == "r":
                filename = raw_input('rename to> ').lower()
                continue
            else:
                return
        try:
            cmd = 'fish-manifest {} -o {}'.format(Settings().tag, filename)
            ShellCommand(cmd).run()
        except Exception as e:
            logging.error(str(e))

    def commit(self):
        try:
            logging.info('Commit manifest with tag ' + Settings().tag)
            subprocess.check_call(['fish-manifest', Settings().tag,
                                   '-r', Settings().codename, '-c'])
            #tag = Settings().tag
            #ubuntuRelease('precise')
            #source_branch = sourceBranch(tag)
            #codename = os.path.basename(source_branch)
            #url = source_branch
            #logging.info('codename:               ' + codename)
            #logging.info('Project Title:          Dell {} {}'.format('precise'
            #                                                         ,tag))
            #logging.info('Project Group:          Somerville')
            #logging.info('Architecture:           amd64')
            #logging.info('Launchpad Project:      dell')
            #logging.info('Config URL:             ' + url)
        except KeyboardInterrupt as e:
            logging.info('^c')
        except Exception as e:
            logging.error(str(e))

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'create':
            self.create()
        elif argv[-1] == 'commit':
            self.commit()
        else:
            self.help()
            return

    def help(self):
        print('Usage: fish-init {} create'.format(self.argv[0]))
        print('  create temporary manifest')
        print('Usage: fish-init {} commit'.format(self.argv[0]))
        print('  commit manifest')

        sys.exit(0)
