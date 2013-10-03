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
#import logging


class Command(CommandBase):
    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return

    def help(self):
        print('Usage: fish-init [-i packages.txt] {}'.format(self.argv[0]))
        print('  Open bugs on launchpad')
        print('  Tasks:')
        print('    1. Fetch modalias list from target(ma.txt)')
        print('    2. Ask modaliases service which packages are needed'
              ' (packages-ma.txt)')
        print('    3. Add common packages and packages from server to '
              'packages.txt')
        #$ find . -type f | xargs md5sum | sort -k 2 > ~/bto_20130203_filelist.txt

        sys.exit(0)
