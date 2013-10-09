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
from mount import Command as Mount
from umount import Command as Umount
from ssh import Command as Ssh
import sys
from shutil import copy
import os
import logging
from random import randint
from os.path import isfile
from os import access


def exit_if_ne_0(ret):
    if ret == 0:
        return
    logging.error('return {} != 0'.format(ret))
    sys.exit(ret)


class Command(CommandBase):
    @property
    def script(self):
        return self.argv[1]

    @property
    def outputs(self):
        if hasattr(self, '_outputs'):
            return self._outputs
        self._outputs = []
        skip = False
        for argv in enumerate(self.argv):
            if skip:
                skip = False
                continue
            if argv[1] == '-o':
                skip = True
                self._outputs.append(self.argv[argv[0] + 1])
        return self._outputs

    def copy_file_back(self, arg):
        filename = os.path.basename(arg)
        if not os.path.exists('./mnt/' + arg):
            logging.error('File not found: ' + arg)
            return
        logging.info('copy result back as ' + filename)
        copy('./mnt/' + arg, filename)

    def execlocal(self):
        argv = self.argv
        is_mount = Mount().is_mount()
        if not is_mount:
            logging.info('mount')
            exit_if_ne_0(Mount().run(argv))
        try:
            script_target = 'execlocal-{0:06d}'.format(randint(0, 999999))
            logging.info('copy {} to target {}'.format(self.script,
                                                       script_target))
            copy(self.script, './mnt/tmp/' + script_target,)

            logging.info('run script...')
            cmd = ['ssh', '/tmp/' + script_target]
            output_index = -1
            for arg in enumerate(self.argv[2:]):
                if arg[1] == '-f':
                    output_index = arg[0] + 3
                    break
                cmd.append(arg[1])
            Ssh().run(cmd)

            if output_index > 0:
                map(self.copy_file_back, argv[output_index:])

            cmd = ['ssh', 'rm', '-f', '/tmp/' + script_target]
            Ssh().run(cmd)
        finally:
            if not is_mount:
                logging.info('umount')
                Umount().run(argv)

    def run(self, argv):
        self.argv = argv
        if len(argv) == 1 or argv[-1] == 'help':
            self.help()
            return
        if not isfile(self.script) or not access(self.script, os.X_OK):
            logging.critical('{} not found or not executable'.
                             format(self.script))
        self.execlocal()

    def help(self):
        print('Usage: fish-init {} <localscript arg1 arg2 ...> '
              '[-f f1 f2 ...]'.format(self.argv[0]))
        print('  Execute localscript on target and copy f1/f2... back')

        sys.exit(0)
