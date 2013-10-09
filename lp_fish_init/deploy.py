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
from diff import Command as Diff
from ssh import Command as Ssh


class Command(CommandBase):
    def revert(self):
        diff = Diff().bto()
        if len(diff['add']) > 0:
            cmd = ['ssh', 'sudo', 'rm', '-f']
            for package in diff['add']:
                logging.info('    {}'.format(package))
                cmd.append(package)
            logging.info('remove {}'.format(' '.join(cmd[4:])))
            Ssh().run(cmd)
        if len(diff['modify']) > 0:
            logging.error('Failed to revert MODIFIED file(s)')
            for package in diff['modify']:
                logging.info('    {}'.format(package))
        if len(diff['delete']) > 0:
            logging.error('Failed to revert DELETED file(s)')
            for package in diff['delete']:
                logging.info('    {}'.format(package))

    def html(self):
        #/usr/bin/extract-manifest-fish -u manifest.html
        pass

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return
        if argv[-1] == 'revert':
            self.revert()
        else:
            self.html()

    def help(self):
        print('Usage: fish-init {} [manifest.html]'.format(self.argv[0]))
        print('  show different files with base image')
        print('Usage: fish-init {} revert'.format(self.argv[0]))
        print('  show different files with base image')

        sys.exit(0)
