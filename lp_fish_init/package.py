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
from lp_fish_tools.util import userEditString


def exit_if_ne_0(ret):
    if ret == 0:
        return
    logging.error('return {} != 0'.format(ret))
    sys.exit(ret)


class Command(CommandBase):
    @property
    def script(self):
        script = '/usr/share/fish-init/modaliases.sh'
        if os.path.exists('./share/modaliases.sh'):
            script = './share/modaliases.sh'
        return script

    @property
    def common_bug_path(self):
        common_bug_path = '/usr/share/fish-init/common-bugs.txt'
        if os.path.exists('./share/common-bugs.txt'):
            common_bug_path = './share/common-bugs.txt'
        return common_bug_path

    @property
    def inputs(self):
        if hasattr(self, '_inputs'):
            return self._inputs
        self._inputs = []
        skip = False
        for argv in enumerate(self.argv):
            if skip:
                skip = False
                continue
            if argv[1] == '-i':
                skip = True
                self._inputs.append(self.argv[argv[0] + 1])
        return self._inputs

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

    def generate_packages(self):
        def reformat_ma_result(lines):
            result = []
            packages = []
            for line in lines:
                fields = line.split()
                if len(fields) != 3:
                    continue
                if fields[1] in packages:
                    continue
                packages.append(fields[1])
                reformat = [fields[0], fields[1], fields[2]]
                result.append(' '.join(reformat) + '\n')
            return result

        # common bugs
        lines = []
        logging.info('Read common bugs from ' + self.common_bug_path)
        with open(self.common_bug_path, 'r') as infile:
            lines += infile.readlines()

        # modaliases packages
        ma_lines = []
        for in_path in self.inputs:
            logging.info('fetch available packages from modaliases service'
                         'as packages-ma.txt for ' + in_path)
            cmd = '{} -i {} -r oem:somerville'.format(self.script, in_path)
            shcmd = ShellCommand(cmd).run()
            with open('packages-ma.txt', 'w+') as f:
                map(lambda line: f.write(line), shcmd.stdout)
            ma_lines += shcmd.stdout.split('\n')
        lines += reformat_ma_result(ma_lines)

        # ask user change it
        lines = userEditString('', ''.join(lines), 'fish-init-pkg')

        logging.info('Save to packages.txt')
        with open('packages.txt', 'w+') as out:
            out.write(lines)
            #map(lambda line: out.write(line + '\n'), lines)

    def generate_ma(self):
        argv = self.argv
        is_mount = Mount().is_mount()
        if not is_mount:
            logging.info('mount')
            exit_if_ne_0(Mount().run(argv))
        try:
            logging.info('copy script to target')
            copy(self.script, './mnt/tmp/modaliases.sh')

            logging.info('run script...')
            Ssh().run(['ssh', '/tmp/modaliases.sh', '-o', '/tmp/ma.txt'])

            logging.info('copy result back as ' + self.outputs[0])
            copy('./mnt/tmp/ma.txt', './' + self.outputs[0])
        finally:
            if not is_mount:
                logging.info('umount')
                Umount().run(argv)

    def run(self, argv):
        self.argv = argv
        if len(argv) == 2 and argv[1] == 'help':
            self.help()
            return

        if len(self.outputs) > 0:
            self.generate_ma()
        elif len(self.inputs) > 0:
            self.generate_packages()
        elif len(self.outputs) == 0 and len(self.inputs) == 0:
            self._outputs = ['ma.txt']
            self.generate_ma()
            self._inputs = ['ma.txt']
            self.generate_packages()
        else:
            self.help()

    def help(self):
        print('Usage: fish-init {}'.format(self.argv[0]))
        print('  Generate packages.txt')
        print('  Tasks:')
        print('    1. Fetch modalias list from target(ma.txt)')
        print('    2. Ask modaliases service which packages are needed'
              ' (packages-ma.txt)')
        print('    3. Add common packages and packages from server to '
              'packages.txt')
        print('')
        print('Usage: fish-init {} [-o ma.txt]'.format(self.argv[0]))
        print('  Gather modaliases from target and save as ma.txt')
        print('')
        print('Usage: fish-init {} [-i ma1.txt [-i ma2.txt ...]]'.
              format(self.argv[0]))
        print('  Generate packages.txt by input file')

        sys.exit(0)
