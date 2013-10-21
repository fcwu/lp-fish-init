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
import requests
import json


class Command(CommandBase):
    @property
    def script(self):
        return Settings().modalias

    def search(self):
        url = Settings().ma_server_address + '/api/v0/search/'
        url += self.argv[-1]
        headers = {'Content-type': 'application/json',
                   'Accept': 'text/plain'}
        #data = {'sender': 'Alice', 'receiver': 'Bob'}
        #r = requests.post(url, data=json.dumps(data), headers=headers)
        r = requests.get(url, headers=headers)
        try:
            data = json.loads(r.content)
            for package in data['modaliases']:
                if package['url'].find('somerville') == -1:
                    continue
                print '{} {}'.format(package['file'], package['modalias'])
        except:
            logging.info('{}'.format(r.content))

    def run(self, argv):
        self.argv = argv
        if argv[-1] == 'help' or len(argv) <= 1:
            self.help()
            return
        self.search()

    def help(self):
        print('Usage: fish-init {} <modalias>'.format(self.argv[0]))
        print('  search <modalias> on modalias service')
        print('  Example:')
        print('    $ fish-init {} 8086d000008b3'.format(self.argv[0]))

        sys.exit(0)
