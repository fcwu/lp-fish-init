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

import os
import sys
from command import CommandBase
from settings import Settings
import subprocess
import logging
from umount import Command as Umount
from ssh import Command as Ssh


class Command(CommandBase):
    def is_mount(self):
        if os.path.ismount('mnt'):
            return True
        return False

    def mount(self):
        if self.is_mount():
            return 0
        if not os.path.exists('mnt'):
            try:
                os.makedirs('mnt')
            except OSError:
                Umount().run(['umount'])
        settings = Settings()
        cmd = ['sshfs', '-F', os.getcwd(), settings.ip + ':/', 'mnt',
               '-o', 'IdentityFile=/usr/share/lp-fish-init/fish-init',
               '-o', 'StrictHostKeyChecking=no',
               '-o', 'UserKnownHostsFile=/dev/null']
        logging.debug(' '.join(cmd))
        result = subprocess.call(cmd)
        logging.info('mount / to mnt: {}'.format(result))
        if result != 0:
            return result
        # FIXME hard code to recovery partition to sda2
        Ssh().run(['ssh', 'sudo', 'mkdir', '-p', '/recovery'])
        for rp in ('/dev/sda2', '/dev/sda3'):
            cmd = ['ssh', 'sudo', 'mountpoint -q /recovery || sudo mount -o uid=$UID {} /recovery'.format(rp)]
            Ssh().run(cmd)
            if os.path.exists(os.path.join('mnt', 'recovery', 'bto.xml')):
                logging.info('mount {} to mnt/recovery: {}'.format(rp, result))
                break
        else:
            logging.warn('failed to mount recovery partition')
        return 0

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        return self.mount()

    def help(self):
        print('Usage: fish-init {}'.format(self.argv[0]))
        print('  mount target\'s root to ./mnt')

        sys.exit(0)
