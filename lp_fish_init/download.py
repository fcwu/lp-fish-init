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
from glob import glob
from os.path import join as pjoin


class FailToBuild(Exception):
    pass


class Command(CommandBase):
    @property
    def zsync_file(self):
        for arg in enumerate(self.argv):
            if '-z' == arg[1]:
                return self.argv[arg[0] + 1]
        return None

    @property
    def project(self):
        return 'dell-bto-' + Settings().codename + '-' + Settings().tag

    @property
    def base_cmd(self):
        return 'ibs-cli -p ' + self.project + ' '

    def wait_build_done(self, build_name):
        while True:
            logging.info('Wait build completed...')
            status = self.build_status(build_name)
            if status is None:
                pass
            if status == 'FAILED':
                logging.critical('Failed to build')
                raise FailToBuild()
            if status == 'COMPLETED':
                break
            sleep(20)
        logging.info('Build completed')

    def build(self):
        build_name_0 = self.get_latest_build()
        logging.info('Ask to build project ' + self.project)
        if ShellCommand(self.base_cmd + 'build').run().returncode != 0:
            logging.critical('Failed to build')
            raise FailToBuild()
        while True:
            logging.info('Wait to build...')
            build_name = self.get_latest_build()
            if build_name not in (build_name_0, 'None'):
                break
            sleep(20)
        return build_name

    def get_latest_build(self):
        cmd = ShellCommand(self.base_cmd + 'list-builds').run()
        if cmd.returncode != 0:
            logging.critical('Failed to list builds')
            return
        build_names = []
        for line in cmd.stdout.split('\n')[1:]:
            fields = [t for t in line.split(' ') if t != '']
            if len(fields) > 0 and fields[2].startswith('201'):
                build_names.append(fields[2])
        build_names.sort()
        if len(build_names) <= 0:
            return None
        return build_names[-1]

    def build_status(self, build_name):
        cmd = ShellCommand(self.base_cmd + 'list-builds').run()
        if cmd.returncode != 0:
            logging.critical('Failed to list builds')
            return
        for line in cmd.stdout.split('\n')[1:]:
            fields = [t for t in line.split(' ') if t != '']
            if fields[2] == build_name:
                return fields[-1]
        return None

    def download(self):
        try:
            # build if needed
            if '-b' in self.argv:
                build_name = self.build()
            else:
                build_name = self.get_latest_build()
            try:
                self.wait_build_done(build_name)
            except FailToBuild:
                logging.critical('{} {} build is failed'.format(self.project,
                                                                build_name))
                return
            # download
            build_name_fields = build_name.split('-')
            while True:
                logging.info('Try downloading... {} {}'.format(self.project,
                                                               build_name))
                cmd_str = self.base_cmd + '-b ' + build_name
                if self.zsync_file is not None:
                    cmd_str += ' -z ' + self.zsync_file
                cmd_str += ' download'
                ShellCommand(cmd_str).run()
                files = glob(pjoin('download',
                                   self.project,
                                   build_name_fields[0],
                                   build_name_fields[1],
                                   'images', '*', '*.iso'))
                if len(files) > 0:
                    logging.info('Done: {}'.format(files[0]))
                    break
                logging.info('ISO is not ready')
                sleep(30)
        except KeyboardInterrupt:
            logging.info('^c')

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return
        self.download()

    def help(self):
        print('Usage: fish-init {} [-b] [-z zsync_base.iso]'.format(
            self.argv[0]))
        print('  download image and build if "-b" is specified')

        sys.exit(0)
