#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright (C) 2012 James Ferguson <james.ferguson@canonical.com>
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
import subprocess
from datetime import datetime

try:
    import DistUtilsExtra.auto
except ImportError:
    print >> sys.stderr, ('To build lp-fish-init you need '
                          'https://launchpad.net/python-distutils-extra')
    sys.exit(1)
assert DistUtilsExtra.auto.__version__ >= '2.18', ('needs DistUtilsExtra.auto'
                                                   '>= 2.18')


class Command(object):
    """Simple subprocess. Popen wrapper to run shell commands and log output
    """
    def __init__(self, command_str, silent=False, verbose=False):
        self.command_str = command_str
        self.silent = silent
        self.verbose = verbose

        self.process = None
        self.stdout = None
        self.stderr = None
        self.time = None

    def run(self):
        """Execute shell command and return output and status
        """
        #logging.debug('Executing: {0!r}...'.format(self.command_str))

        self.process = subprocess.Popen(self.command_str,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        start = datetime.now()
        result = self.process.communicate()
        end = datetime.now()
        self.time = end - start

        self.returncode = self.process.returncode
        if self.returncode != 0 or self.verbose:
            stdout, stderr = result
            message = ['Output:'
                       '- returncode:\n{0}'.format(self.returncode)]
            if stdout:
                if type(stdout) is bytes:
                    stdout = stdout.decode()
                message.append('- stdout:\n{0}'.format(stdout))
            if stderr:
                if type(stderr) is bytes:
                    stderr = stderr.decode()
                message.append('- stderr:\n{0}'.format(stderr))
            #if not self.silent:
            #    logging.debug('\n'.join(message))

            self.stdout = stdout
            self.stderr = stderr

        if self.returncode != 0:
            print(self.returncode,
                  '{0}: {1}'.format(self.command_str,
                  self.stderr))

        return self


class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        Command('share/builder.sh').run()
        DistUtilsExtra.auto.install_auto.run(self)


DistUtilsExtra.auto.setup(
    name='lp-fish-init',
    version='0.1',
    license='GPL-3',
    author='Doro Wu',
    author_email='doro.wu@canonical.com',
    description='Provides fish-init command for OEM Dell enablement',
    cmdclass={'install': InstallAndUpdateDataDirectory}
    #long_description='Here a longer description',
    #url='https://launchpad.net/lp-fish-tools',
)
