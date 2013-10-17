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
import logging
from settings import Settings
from shellcommand import ShellCommand
from time import sleep


class Command(CommandBase):
    @property
    def zsync_file(self):
        for arg in enumerate(self.argv):
            if '-z' == arg[1]:
                return self.argv[arg[0] + 1]
        return None

    @property
    def project(self):
        return 'dell-bto-precise-' + Settings().tag

    @property
    def base_cmd(self):
        return 'ibs-cli -p ' + self.project + ' '

    def download(self):
        try:
            # list builds
            cmd = ShellCommand(self.base_cmd + 'list-builds').run()
            if cmd.returncode != 0:
                logging.critical('Failed to list builds')
                return
            builds_0 = cmd.stdout.split('\n')
            # build if needed
            if '-b' in self.argv:
                logging.info('Ask to build project ' + self.project)
                if ShellCommand(self.base_cmd + 'build').run().returncode != 0:
                    logging.critical('Failed to build')
                    return
            # detect finish
            logging.info('Detecting...')
            build_sn = None
            line_before = None
            is_completed = False
            while not is_completed:
                sleep(5)
                cmd = ShellCommand(self.base_cmd + 'list-builds').run()
                if cmd.returncode != 0:
                    logging.critical('Failed to list builds')
                    return
                builds_1 = cmd.stdout.split('\n')
                difference = set(builds_1) - set(builds_0)
                if len(difference) == 0:
                    logging.info('Waiting for build creating...')
                    continue
                #INFO - 20131017-2 - 2013-10-17T02:23:38 - 2013-10-17T02:26:58\
                #        - COMPLETED
                for line in difference:
                    fields = [t for t in line.split(' ') if t != '']
                    if build_sn is None:
                        if fields[2] == 'None':
                            break
                        build_sn = fields[2]
                        line_before = line
                        logging.info('Build Name = {}'.format(build_sn))
                        break
                    if build_sn == fields[2]:
                        if line_before != line:
                            logging.info('Status changed: {}'.format(fields[-1]))
                        if fields[-1] in ('COMPLETED', 'FAILED'):
                            is_completed = True
                        break
            # download
            cmd_str = self.base_cmd + '-b ' + build_sn + ' download'
            cmd = ShellCommand(cmd_str).run()
            if cmd.returncode != 0:
                logging.critical('Failed to download')
        except KeyboardInterrupt:
            logging.info('^c')

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return
        self.download()

    def help(self):
        print('Usage: fish-init {} [-b] [-z zsync_base.iso]'.format(self.argv[0]))
        print('  download image and build if "-b" is specified')

        sys.exit(0)
