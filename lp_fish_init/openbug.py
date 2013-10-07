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
import os
import logging
import subprocess
from lp_fish_tools.util import EditableData
from lp_fish_tools.util import splitInputValues as split_tags
from settings import Settings
import webbrowser
from launchpadlib.launchpad import Launchpad
import hashlib


MODALIAS_DESCRIPTION = '''
This bug is opened by fish-init because of modalias matched
{modalias}

X-Dell-Fixed-By:{package} {md5}
X-Dell-Subsystem-Category:<fill category>
'''


class Command(CommandBase):
    @property
    def error_lines(self):
        if hasattr(self, '_error_lines'):
            return self._error_lines
        self._error_lines = []
        return self._error_lines

    @property
    def script(self):
        script = '/usr/share/fish-init/modaliases.sh'
        if os.path.exists('./share/modaliases.sh'):
            script = './share/modaliases.sh'
        return script

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
        if len(self._inputs) <= 0:
            self._inputs.append('packages.txt')
        return self._inputs

    @property
    def lp(self):
        if hasattr(self, '_lp'):
            return self._lp
        cachedir = os.path.join(os.environ["HOME"], ".launchpadlib/cache")
        lp = Launchpad.login_with("lp-fish-tools", 'production', cachedir)
        if not lp:
            logging.fatal('failed to connect to launchpad')
        self._lp = lp
        return self._lp

    def openbug_ma(self, line):
        dest_basepath = 'pool'
        project = 'dell'
        title = ('Need driver package support for <module name> [<device id>]')
        try:
            if not os.path.exists(dest_basepath):
                os.mkdir(dest_basepath)
            modalias, package, download_params = line.split(' ', 3)
            # download
            filename = os.path.join(dest_basepath, package)
            logging.info('Downloading {}'.format(filename))
            subprocess.check_call(['wget', '{}/api/v0/download/{}?{}'.format(
                                   Settings().ma_server_address,
                                   package, download_params),
                                   '-O', filename])
            # md5sum
            md5 = hashlib.md5(open(filename).read()).hexdigest()
            description = MODALIAS_DESCRIPTION.format(modalias=modalias,
                                                      package=package,
                                                      md5=md5)
            editable = EditableData(description,
                                    {'Projects': project,
                                     'Tags': Settings().tag,
                                     'Title': title})
            while True:
                logging.info("Passing bug description to user for editing")
                editable.userEdit()

                # user confirmation
                inp = raw_input('Continue? [y]es/[r]eview/[n]o]> ').lower()
                if inp == "y":
                    break
                elif inp == "r":
                    continue
                else:
                    logging.info("Quitting at user request")
                    self.error_lines.append(line)
                    return

            # create new bug and add targets
            logging.info("Creating new bug")
            tags = split_tags(editable.namedValues["Tags"])
            create_bug = self.lp.bugs.createBug
            newBug = create_bug(description=editable.baseText,
                                private=True,
                                security_related=False,
                                tags=tags,
                                target=project,
                                title=editable.namedValues["Title"])
            logging.info('New bug created: %d - opening in browser...' %
                         newBug.id)
            url = 'https://bugs.launchpad.net/bugs/%d' % newBug.id
            webbrowser.open(url)
            logging.info('Done')
        except Exception as e:
            logging.error('{}: Open bug for {}'.format(e, line))
            self.error_lines.append(line)

    def openbug_lp(self, line):
        try:
            bugnum = line.split(' ', 2)[0][3:]
            subprocess.check_call(['dup-bug', str(bugnum)])
        except Exception as e:
            logging.error('{}: Open bug for {}'.format(e, line))
            self.error_lines.append(line)

    def openbug_line(self, line):
        line = line.strip()
        if line.startswith('#'):
            return
        if line.startswith('LP:'):
            self.openbug_lp(line)
        else:
            self.openbug_ma(line)

    def openbug_file(self, filename):
        if not os.path.exists(filename):
            logging.error('file not found: ' + filename)
            return
        lines = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                lines.append(line)
        for line in enumerate(lines):
            logging.info('In progress... {}/{}'.format(line[0], len(lines)))
            logging.info('Open bug for {}'.format(line[1]))
            self.openbug_line(line[1])

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help':
            self.help()
            return
        map(self.openbug_file, self.inputs)
        if len(self.error_lines) > 0:
            logging.info('Following bugs didn\'t open')
        for line in self.error_lines:
            logging.info('    ' + line)

    def help(self):
        print('Usage: fish-init [-i packages.txt] {}'.format(self.argv[0]))
        print('  Open bugs on launchpad')

        sys.exit(0)
