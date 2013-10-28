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
import os
from settings import Settings
from execlocal import Command as ExecLocal


class Command(CommandBase):
    def read_fileitems(self, inp):
        items = {}
        for line in inp:
            fields = line.strip().split(' ', 2)
            items[fields[2]] = fields[0]
        return items

    def bto(self, argv=None):
        result = {'add': [], 'modify': [], 'delete': []}
        ExecLocal().run(['execlocal', Settings().recovery_filelist_path,
                        '-f', '/tmp/recovery-filelist.txt'])
        bto = self.read_fileitems(open(Settings().filelist_path, 'r'))
        target = self.read_fileitems(open('recovery-filelist.txt', 'r'))
        for item in target:
            if item in bto:
                if target[item] != bto[item]:
                    result['modify'].append(item)
                del bto[item]
            else:
                result['add'].append(item)
        for item in bto:
            result['delete'].append(item)
        for key in result:
            result[key].sort()
        return result

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'bto':
            diff = self.bto()
            logging.info('ADD')
            for package in diff['add']:
                logging.info('    {}'.format(package))
            logging.info('MODIFY')
            for package in diff['modify']:
                logging.info('    {}'.format(package))
            logging.info('DELETE')
            for package in diff['delete']:
                logging.info('    {}'.format(package))
        elif argv[-1] == 'commit':
            self.commit()
        else:
            self.help()
            return

    def help(self):
        print('Usage: fish-init {} bto'.format(self.argv[0]))
        print('  show different files with base image')

        sys.exit(0)
