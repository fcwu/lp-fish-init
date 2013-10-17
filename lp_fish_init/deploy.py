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
from diff import Command as Diff
#from ssh import Command as Ssh
from scp import Command as Scp
from execlocal import Command as ExecLocal
from lp_fish_tools.ManifestFileData import ManifestFileData
from lp_fish_tools.SomervilleShare import SomervilleShare
from settings import Settings
from shellcommand import ShellCommand
from datetime import datetime
import hashlib
import os


class Command(CommandBase):
    def revert_remove_files(self, files):
        with open('remove-list.txt', 'w') as f:
            f.write('\n'.join(files))
            f.write('\n')

        if Scp().run(['scp', 'remove-list.txt', '/tmp/']) != 0:
            logging.critical('Failed to copy {} to target'.format(
                             'remove-list.txt'))
            return False
        script = Settings().recovery_remove_path
        if ExecLocal().run(['execlocal', script, '/tmp/remove-list.txt']) != 0:
            logging.critical('Error when running {}'.format(script))
            return False
        return True

    def revert(self):
        result = True
        diff = Diff().bto()
        if len(diff['add']) > 0:
            logging.info('remove {}'.format(' '.join(diff['add'])))
            if not self.revert_remove_files(diff['add']):
                result = False
        if len(diff['modify']) > 0:
            logging.error('Failed to revert MODIFIED file(s)')
            for package in diff['modify']:
                logging.info('    {}'.format(package))
            result = False
        if len(diff['delete']) > 0:
            logging.error('Failed to revert DELETED file(s)')
            for package in diff['delete']:
                logging.info('    {}'.format(package))
            result = False
        return result

    @property
    def manifest_path(self):
        return self.argv[-1]

    def download_verify_fixes(self, f):
        localname = os.path.join(Settings().pool_path, f.name)
        downloaded = False
        for i in xrange(0, 2):
            if not os.path.exists(localname):
                logging.info('Downloading ' + f.name)
                svshare = SomervilleShare()
                svshare.download_fish(f.name)
                os.rename(f.name, localname)
                downloaded = True
            md5 = hashlib.md5(open(localname).read()).hexdigest()
            if md5 != f.md5_hash and downloaded:
                return False
        return True
        #logging.info('{} {} {}'.format(f.name, f.md5_hash, f.url()))

    def html(self):
        if not os.path.exists(self.manifest_path):
            logging.critical('Manifest not found: ' + self.manifest_path)
            return

        logging.info('Revert to base version: {}'.format(
                     Settings().bto_version))
        if not self.revert():
            logging.warn('Some file(s) cannot revert')
            inp = raw_input('Continue? [y]es/[N]o]> ').lower()
            if inp != "y":
                return

        manifest = ManifestFileData(self.manifest_path)
        #logging.info("Manifest for project: %s", manifest.project_name)
        fixes = [f for f in manifest.fix_info.keys()]

        for f in fixes:
            if not self.download_verify_fixes(f):
                logging.critical('checksum mismatch: ' + f.name)
                return

        # tar fixes
        tarball = '{}-{}.tar'.format(manifest.project_name,
                                     datetime.now().strftime("%y%m%d-%H%M%S"))
        files = ' '.join([f.name for f in fixes])
        cmd = 'tar cvf {} -C pool {}'.format(tarball, files)
        if ShellCommand(cmd).run().returncode != 0:
            logging.critical('Failed to tar FISH(es): {}'.format(cmd))
            return
        # scp to /tmp/
        if Scp().run(['scp', tarball, '/tmp/']) != 0:
            logging.critical('Failed to copy {} to target'.format(tarball))
            return
        # call execlocal to mount recovery and untar
        script = Settings().recovery_deploy_path
        if ExecLocal().run(['execlocal', script, '/tmp/' + tarball]) != 0:
            logging.critical('Error when running {}'.format(script))
            return

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return
        if argv[-1] == 'revert':
            if not self.revert():
                logging.critical('Failed to revert')
        else:
            self.html()

    def help(self):
        print('Usage: fish-init {} [manifest.html]'.format(self.argv[0]))
        print('  deploy fixes in manifest.html to target recovery partition')
        print('Usage: fish-init {} revert'.format(self.argv[0]))
        print('  Revert recovery partition without fixes')

        sys.exit(0)
