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
from shellcommand import ShellCommand
import os
import logging


def exit_if_ne_0(ret):
    if ret == 0:
        return
    logging.error('return {} != 0'.format(ret))
    sys.exit(ret)


class Command(CommandBase):
    def run(self, argv):
        def reformat_ma_result(lines):
            result = []
            for line in lines.split('\n'):
                fields = line.split()
                if len(fields) != 3:
                    continue
                reformat = [fields[0], fields[1], fields[2]]
                result.append(' '.join(reformat))
            return result

        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        logging.info('mount')
        is_mount = Mount().is_mount()
        if not is_mount:
            exit_if_ne_0(Mount().run(argv))
        try:
            script = '/usr/share/fish-init/modaliases.sh'
            if os.path.exists('./share/modaliases.sh'):
                script = './share/modaliases.sh'
            common_bug_path = '/usr/share/fish-init/common-bugs.txt'
            if os.path.exists('./share/common-bugs.txt'):
                common_bug_path = './share/common-bugs.txt'

            logging.info('copy script to target')
            copy(script, './mnt/tmp/modaliases.sh')

            logging.info('run script...')
            Ssh().run(['ssh', '/tmp/modaliases.sh', '-o', '/tmp/ma.txt'])

            logging.info('copy result back as ma.txt')
            copy('./mnt/tmp/ma.txt', './ma.txt')

            logging.info('fetch available packages from modaliases service'
                         'as packages-ma.txt')
            cmd = '{} -i ma.txt -r oem:somerville'.format(script)
            shcmd = ShellCommand(cmd).run()
            with open('packages-ma.txt', 'w+') as f:
                map(lambda line: f.write(line), shcmd.stdout)

            logging.info('insert somerville-common bugs')
            with open(common_bug_path, 'r') as infile:
                with open('packages.txt', 'w+') as out:
                    out.writelines(infile.xreadlines())
                    lines = reformat_ma_result(shcmd.stdout)
                    map(lambda line: out.write(line + '\n'), lines)

            logging.info('=' * 80)
            logging.info('= Modify packages.txt before openbugs')
            logging.info('=' * 80)
        finally:
            if not is_mount:
                logging.info('umount')
                Umount().run(argv)

    def help(self):
        print 'Usage: fish-init {}'.format(self.argv[0])
        print '  mount target\'s root to ./mnt'

        sys.exit(0)
