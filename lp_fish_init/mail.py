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

import sys
from command import CommandBase
from settings import Settings
import subprocess
from lp_fish_tools.SomervilleShare import SomervilleShare
from download import Command as Download
import logging
from glob import glob
import os
import urllib


TITLE = '[canonical-dell-team] {VER} manifest for {PLATFORM}'
TO = 'canonical-dell-team@lists.canonical.com'
TEMPLATE = """Hi,<br/>
<br/>
Please find links below the {VER} manifest of {PLATFORM}.<br/>
<br/>
Manifest:<br/>
{MANIFEST}<br/>
<br/>
ISO:<br/>
{ISO}<br/>
<br/>
ISO Checksums:<br/>
MD5: {MD5}<br/>
SHA-1: {SHA1}<br/>
<br/>
Verification:<br/>
Installation: [Yes/No]<br/>
S3: [Yes/No]<br/>
<br/>
Regards,<br/>
[NAME]<br/>
"""


class Command(CommandBase):
    def mail(self):
        svshare = SomervilleShare()
        platform = Settings().tag
        codename = Settings().codename
        version = svshare.manifest_url(platform)
        latest_path = Download().get_latest_build()
        manifest_url = ('/'.join(svshare.base_url.split('/')[:3]) +
                        '/partners/somerville/share/' +
                        svshare.conn.path.split('/', 3)[-1])
        iso_dirname = os.path.join('download',
                                   'dell-bto-' + codename + '-' + platform,
                                   latest_path.replace('-', '/'),
                                   'images',
                                   'iso')
        file_matches = glob(os.path.join(iso_dirname, '*.iso'))
        if len(file_matches) <= 0:
            logging.info('No iso found in ' + iso_dirname)
            logging.info('Please run download first')
            return
        iso_url = ('https://oem-share.canonical.com/oem/cesg-builds/'
                   '{}').format(file_matches[0].split('/', 1)[1])
        md5 = ''
        file_matches = glob(os.path.join(iso_dirname, '*.md5sums.txt'))
        if len(file_matches) > 0:
            with open(file_matches[0], 'r') as f:
                md5 = f.readline().split()[0]
        sha1 = ''
        file_matches = glob(os.path.join(iso_dirname, '*.sha1sums.txt'))
        if len(file_matches) > 0:
            with open(file_matches[0], 'r') as f:
                sha1 = f.readline().split()[0]
        content = TEMPLATE.format(VER=version,
                                  PLATFORM=platform,
                                  ISO=iso_url,
                                  MANIFEST=manifest_url,
                                  MD5=md5,
                                  SHA1=sha1)
        subprocess.call('printf "' + content + '"|xclip -selection clipboard',
                        shell=True)
        to = urllib.quote(TO)
        title = urllib.quote(TITLE.format(VER=version, PLATFORM=platform))
        subprocess.call('firefox mailto:{}?subject={}'.format(to,
                        title), shell=True)

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        return self.mail()

    def help(self):
        print('Usage: fish-init {} file1 [file2 ...] dest'.format(
              self.argv[0]))
        print '  copy file(s) to target'

        sys.exit(0)
