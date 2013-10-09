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
import ConfigParser

# arguments and help
# logging

INIT_FILE = 'FishInitFile'


class Settings(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Settings, cls).__new__(
                                  cls, *args, **kwargs)
        return cls._instance

    @property
    def config(self):
        if hasattr(self, '_config'):
            return self._config
        if os.path.exists(INIT_FILE):
            self._config = ConfigParser.RawConfigParser()
            self._config.read(INIT_FILE)
        else:
            self._config = ConfigParser.RawConfigParser()
            self._config.add_section('basic')
        return self._config

    def commit(self):
        if not hasattr(self, '_config'):
            return
        with open(INIT_FILE, 'wb') as configfile:
            self.config.write(configfile)

    @property
    def ip(self):
        return self.get('basic', 'ip')

    @ip.setter
    def ip(self, value):
        self.set('basic', 'ip', value)

    @property
    def tag(self):
        return self.get('basic', 'tag')

    @tag.setter
    def tag(self, value):
        self.set('basic', 'tag', value)

    @property
    def ma_server_address(self):
        return 'http://162.213.34.36:5566'

    @property
    def bto_version(self):
        return '20130203'

    @property
    def filelist_path(self):
        version = Settings().bto_version
        if os.path.exists('./share/bto-' + version + '-filelist.txt'):
            return './share/bto-' + version + '-filelist.txt'
        return '/usr/share/fish-init/bto-' + version + '-filelist.txt'

    @property
    def recovery_filelist_path(self):
        if os.path.exists('./share/recovery-filelist.sh'):
            return './share/recovery-filelist.sh'
        return '/usr/share/fish-init/recovery-filelist.sh'

    def get(self, section, name):
        value = ''
        try:
            value = self.config.get(section, name)
        except Exception:
            pass
        return value

    def set(self, section, name, value):
        try:
            self.config.set(section, name, value)
        except Exception:
            pass
