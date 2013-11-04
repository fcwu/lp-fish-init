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
from settings import Settings
import webbrowser


class Command(CommandBase):
    def run(self, argv):
        self.argv = argv
        if len(self.argv) <= 1:
            webbrowser.open(Settings().ma_server_address)
            return
        try:
            bug_num = int(self.argv[1])
            webbrowser.open('https://bugs.launchpad.net/dell/+bug/{}'
                            .format(bug_num))
            return
        except ValueError:
            pass
        webbrowser.open('https://bugs.launchpad.net/dell/+bugs?field.tag={}'
                        .format(self.argv[1]))

    def help(self):
        print('Usage: fish-init {}'.format(self.argv[0]))
        print('  Open modalias service in browser')
        print('Usage: fish-init {} <1234567>'.format(self.argv[0]))
        print('  Open modalias service in browser')
        print('Usage: fish-init {} <platform-tag>'.format(self.argv[0]))
        print('  Open modalias service in browser')

        sys.exit(0)
