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
import subprocess
import logging
from ssh import Command as Ssh


class Command(CommandBase):
    def umount(self):
        Ssh().run(['ssh', 'sudo', 'umount', '/recovery'])
        Ssh().run(['ssh', 'sudo', 'rmdir', '/recovery'])
        cmd = ['fusermount', '-u', 'mnt']
        logging.debug(' '.join(cmd))
        return subprocess.call(cmd)

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        return self.umount()

    def help(self):
        logging.info('Usage: fish-init {}'.format(self.argv[0]))
        logging.info('  umount ./mount')

        sys.exit(0)
