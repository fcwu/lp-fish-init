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
import logging

# arguments and help
# logging


class Command(CommandBase):
    def run(self, argv):
        self.argv = argv
        if argv[1] == 'help':
            self.help()
            return

    def help(self):
        print 'Usage: {} ip tag'.format(self.argv[0])
        print 'Example:'
        print '  {} 192.168.0.10 general-sff'.format(self.argv[0])
        sys.exit(0)
