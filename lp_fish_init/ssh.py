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
import subprocess
import logging
import os


class Command(CommandBase):
    def ssh(self):
        settings = Settings()
        cmd = ['ssh', '-F', os.getcwd(), settings.ip, '-q', '-i',
               '/usr/share/lp-fish-init/fish-init',
               '-o', 'StrictHostKeyChecking=no',
               '-o', 'UserKnownHostsFile=/dev/null']
        if len(self.argv) > 1:
            cmd += self.argv[1:]
        logging.debug(' '.join(cmd))
        return subprocess.call(cmd)

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        return self.ssh()

    def help(self):
        logging.info('Usage: fish-init {} [command]'.format(self.argv[0]))
        logging.info('Example:')
        logging.info('  # login to target')
        logging.info('    $ fish-init {}'.format(self.argv[0]))
        logging.info('  # Run dpkg -l on target')
        logging.info('    $ fish-init {} dpkg -l'.format(self.argv[0]))

        sys.exit(0)
