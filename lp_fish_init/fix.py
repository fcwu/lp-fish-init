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
from lp_fish_tools.SomervilleShare import SomervilleShare as SShare
from webdav.WebdavClient import CollectionStorer
from download import Command as Download
import logging
from glob import glob
import os
from os.path import join as pjoin
import urllib
from operator import itemgetter


class InvalidPackage(Exception):
    def __init__(self, package):
        self.package = package

    def __str__(self):
        return 'Package not found: {}'.format(self.package)


class SomervilleShare(SShare):
    def __init__(self):
        SShare.__init__(self)
        self._cache = {}

    def list(self, url):
        if not url.endswith('/'):
            url += '/'
        if url in self._cache:
            return self._cache[url]
        self.conn = CollectionStorer(pjoin(self.base_url, url),
                                     validateResourceNames=False)
        self.conn.connection.addBasicAuthorization(self.user, self.passwd)
        filenames = []
        for res in self.conn.getCollectionContents():
            fn = res[0].path.split('/')[-1]
            filenames.append(fn)
        self._cache[url] = filenames
        return filenames


class Command(CommandBase):
    @property
    def fixes(self):
        if hasattr(self, '_fixes'):
            return self._fixes
        self._prepare_arguments()
        return self._fixes

    @property
    def bugs(self):
        if hasattr(self, '_bugs'):
            return self._bugs
        self._prepare_arguments()
        return self._bugs

    @property
    def categories(self):
        if hasattr(self, '_categories'):
            return self._categories
        self._prepare_arguments()
        return self._categories

    @property
    def svshare(self):
        if hasattr(self, '_svshare'):
            return self._svshare
        self._svshare = SomervilleShare()
        return self._svshare

    @property
    def base_pkgs(self):
        if hasattr(self, '_base_pkgs'):
            return self._base_pkgs
        self._base_pkgs = {}
        with open(Settings().bto_pkgs_path, 'r') as f:
            for line in f:
                fields = self.split_package_name(line.strip())
                self._base_pkgs[fields[0]] = fields
        return self._base_pkgs

    def _prepare_arguments(self):
        self._bugs = []
        self._fixes = []
        self._categories = []
        skip = 0
        for arg in self.argv[1:]:
            if skip > 0:
                self._categories.append(arg)
                skip -= 1
                continue
            if arg == '-c':
                skip = 1
                continue
            try:
                self._bugs.append(int(arg))
            except ValueError:
                self._fixes.append(arg)

    def find_latest_package(self, package):
        filenames = self.svshare.list(pjoin('pool', package[0]))
        logging.debug(str(filenames))
        candicates = []
        for f in filenames:
            if not f.endswith('.deb'):
                continue
            if f.startswith(package):
                name, ver, arch = self.split_package_name(f)
                if name == package:
                    candicates.append((name, ver, arch))
        candicates = sorted(candicates, key=itemgetter(1), reverse=True)
        logging.debug('candicates: ' + str(candicates))
        if len(candicates) <= 0:
            raise InvalidPackage(package)
        return '_'.join(candicates[0]) + '.deb'

    def split_package_name(self, package):
        if not package.endswith('.deb'):
            package = self.find_latest_package(package)
        return package.rstrip('.deb').split('_', 3)

    def package_exist_svshare(self, package):
        filenames = self.svshare.list(pjoin('pool', package[0]))
        for f in filenames:
            if f == package:
                return
        raise InvalidPackage(package)

    def formalize_package(self, package):
        if not package.endswith('.deb'):
            package = self.find_latest_package(package)
        else:
            self.package_exist_svshare(package)
        return package

    def find_package_depends(self, package):
        dest_basepath = Settings().pool_path
        if not os.path.exists(dest_basepath):
            os.mkdir(dest_basepath)
        filename = os.path.join(dest_basepath, package)
        if not os.path.exists(filename):
            self.svshare.download_fish(package)
            os.rename(package, filename)
        output = subprocess.check_output(['dpkg', '-I', filename])
        depends = filter(lambda line: line.startswith(' Depends:'),
                         output.split('\n'))
        if len(depends) <= 0:
            return []
        depends = depends[0][10:]
        brokens = []
        for depend in depends.split(', '):
            if len(depend.strip()) == 0:
                continue
            if depend.find(' ') == -1:
                if depend not in self.base_pkgs:
                    brokens.append((depend, None, None))
                continue
            name, op, ver = depend.split(' ', 3)
            op = op[1:].strip()
            ver = ver[:-1]
            logging.debug('{}_{}_{}'.format(name, op, ver))
            if name not in self.base_pkgs:
                brokens.append((name, op, ver))
                continue
            #< << <= = >= >> >
            if op in ('<', '<<'):
                if ver >= self.base_pkgs[name]:
                    brokens.append((name, op, ver))
            elif op == '<=':
                if ver > self.base_pkgs[name]:
                    brokens.append((name, op, ver))
            elif op == '=':
                if ver != self.base_pkgs[name]:
                    brokens.append((name, op, ver))
            elif op == '>=':
                if ver < self.base_pkgs[name]:
                    brokens.append((name, op, ver))
            elif op in ('>', '>>'):
                if ver <= self.base_pkgs[name]:
                    brokens.append((name, op, ver))

        return brokens


    def fix(self):
        logging.debug('fixes: ' + str(self.fixes))
        logging.debug('bugs: ' + str(self.bugs))
        logging.debug('categories: ' + str(self.categories))
        fixes = self.fixes
        fixes_depends = []
        for fix in enumerate(fixes):
            fixes[fix[0]] = self.formalize_package(fix[1])
            logging.debug(str(fixes[fix[0]]))
            name, ver, arch = self.split_package_name(fixes[fix[0]])
            depends = self.find_package_depends(fixes[fix[0]])
            logging.debug('brokens: ' + str(depends))
        #if any('update-base-essential-precise-all' in self.fixes:
        #    fixes.append(
        #        self.find_depends('update-base-essential-precise-all'))
        #svshare = SomervilleShare()
        #platform = Settings().tag
        #codename = Settings().codename
        #version = svshare.manifest_url(platform)
        #latest_path = Download().get_latest_build()
        #manifest_url = ('/'.join(svshare.base_url.split('/')[:3]) +
        #                '/partners/somerville/share/' +
        #                svshare.conn.path.split('/', 3)[-1])
        #iso_dirname = os.path.join('download',
        #                           'dell-bto-' + codename + '-' + platform,
        #                           latest_path.replace('-', '/'),
        #                           'images',
        #                           'iso')
        #file_matches = glob(os.path.join(iso_dirname, '*.iso'))
        #if len(file_matches) <= 0:
        #    logging.info('No iso found in ' + iso_dirname)
        #    logging.info('Please run download first')
        #    return
        #iso_url = ('https://oem-share.canonical.com/oem/cesg-builds/'
        #           '{}').format(file_matches[0].split('/', 1)[1])
        #md5 = ''
        #file_matches = glob(os.path.join(iso_dirname, '*.md5sums.txt'))
        #if len(file_matches) > 0:
        #    with open(file_matches[0], 'r') as f:
        #        md5 = f.readline().split()[0]
        #sha1 = ''
        #file_matches = glob(os.path.join(iso_dirname, '*.sha1sums.txt'))
        #if len(file_matches) > 0:
        #    with open(file_matches[0], 'r') as f:
        #        sha1 = f.readline().split()[0]
        #logging.info('test')
        return

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        return self.fix()

    def help(self):
        print('Usage: fish-init {} [-c category] file1 [file2 ...] bug_num1 [bug_num2 ...]'.format(
              self.argv[0]))
        print '  fix bugs'

        sys.exit(0)
