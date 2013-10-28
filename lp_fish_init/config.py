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

import sys
from command import CommandBase
from settings import Settings

# arguments and help
# logging


class Command(CommandBase):
    def set(self):
        s = Settings()
        s.ip = self.argv[1]
        if s.ip.find('@') == -1:
            s.ip = 'u@' + s.ip
        s.tag = self.argv[2]
        s.commit()
        self.get()

    def get(self):
        settings = Settings()
        print 'IP = {}'.format(settings.ip)
        print 'LP Tag = {}'.format(settings.tag)

    def run(self, argv):
        self.argv = argv
        if len(argv) == 1:
            self.get()
            return
        if len(argv) == 3:
            self.set()
            return
        self.help()

    def help(self):
        description = 'Set/Get current working target Launchpad tag and IP'
        print 'Usage: fish-init {} [ip tag]'.format(self.argv[0])
        print '    ' + description
        print 'Example:'
        print '  $ fish-init {} 192.168.0.10 general-sff'.format(self.argv[0])
        print '  $ fish-init {} '.format(self.argv[0])
        print '  IP = 192.168.0.10'
        print '  LP Tag = general-sff'

        sys.exit(0)
