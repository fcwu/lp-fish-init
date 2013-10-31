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
import logging
import os
from os.path import join as pjoin
import apt_pkg
import requests
import json
import shutil


apt_pkg.InitSystem()


class InvalidPackage(Exception):
    def __init__(self, package):
        self.package = package

    def __str__(self):
        return 'Package not found: {}'.format(self.package)


class InvalidDpkgCompareOp(Exception):
    def __init__(self, d1, op, d2):
        self.data = (d1, op, d2)

    def __str__(self):
        return 'Invalid debian comparing operation: {}, {}, {}'.format(
               self.data[0], self.data[1], self.data[2])


class BaseStringException(Exception):
    def __init__(self, data=None):
        self._data = data

    def __str__(self):
        if self._data is None:
            return self.__class__.__name__
        return '{}: {}'.format(self.__class__.__name__, self._data)


class ModaliasesServiceError(BaseStringException):
    pass


class PackageNotFoundError(BaseStringException):
    pass


class DownloadError(BaseStringException):
    pass


class BrokenDependsError(BaseStringException):
    pass


class ValidateDepend(object):
    def __init__(self, base):
        self._base = base

    @staticmethod
    def depends_line(filename):
        output = subprocess.check_output(['dpkg', '-I', filename])
        depends = filter(lambda line: line.startswith(' Depends:'),
                         output.split('\n'))
        if len(depends) <= 0:
            return None
        depends = depends[0][10:]
        return depends

    @staticmethod
    def split_line2rule(line):
        for rule in line.split(', '):
            yield rule.strip()

    @staticmethod
    def split_rule2item(depend):
        for item in depend.split('|'):
            yield item.strip()

    @staticmethod
    def split_item(item):
        # item without version, such as "aaa (>= 1.2)"
        if item.find('(') == -1:
            return (item, None, None)
        name, op, ver = item.split(' ', 3)
        op = op[1:].strip()
        ver = ver[:-1]
        return (name, op, ver)

    def validate_item(self, item):
        item = item.strip()
        name, op, ver = self.__class__.split_item(item)
        logging.debug('checking: {}, {}, {}'.format(name, op, ver))
        if name not in self._base:
            return False
        if op is None:
            return True
        return compare_dpkg_version(self._base[name], op, ver)

    def validate(self, filename):
        cls = self.__class__
        line = cls.depends_line(filename)
        if line is None:
            return []
        brokens = []
        for rule in cls.split_line2rule(line):
            for item in cls.split_rule2item(rule):
                if self.validate_item(item):
                    break
            else:
                brokens.append(rule)
        return brokens


def compare_dpkg_version(d1, op, d2):
    compare_result = apt_pkg.VersionCompare(d1, d2)
    logging.debug('compare_dpkg_version: {}, {}, {}'.format(d1, op, d2))
    # VersionCompare result > 0 if 1 > 2
    #                       < 0 if 1 < 2
    # op: < << <= = >= >> >
    # op: lt, le, eq, ne, ge, gt
    if op in ('<', '<<', 'lt'):
        if compare_result < 0:
            return True
    elif op in ('<=', 'le'):
        if compare_result <= 0:
            return True
    elif op in ('=', 'eq'):
        if compare_result != 0:
            return True
    elif op in ('>=', 'ge'):
        if compare_result >= 0:
            return True
    elif op in ('>', '>>', 'gt'):
        if compare_result > 0:
            return True
    else:
        raise InvalidDpkgCompareOp(d1, op, d2)
    return False


def sort_dpkg(filenames, reverse=True):
    def compare(d1, d2):
        result = 0
        if compare_dpkg_version(d1[1], '>', d2[1]):
            result = 1
        elif compare_dpkg_version(d1[1], '<', d2[1]):
            result = -1
        return result
    return sorted(filenames, cmp=compare, reverse=reverse)


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

    def find_latest_package(self, package):
        candidates = self.search_package(package)
        logging.debug('candidates: ' + str(candidates))
        if len(candidates) <= 0:
            raise PackageNotFoundError(package)
        return '_'.join(candidates[0]) + '.deb'

    def package_exist(self, package):
        if len(self.search_package(package)) <= 0:
            raise PackageNotFoundError(package)
        return True

    def search_package(self, package):
        logging.info('Searching {} in SomervilleShare'.format(package))
        filenames = self.list(pjoin('pool', package[0]))
        search_key = package
        candidates = []
        if not search_key.endswith('.deb'):
            search_key += '_'
        #logging.debug('In pool {}: {}'.format(search_key, filenames))
        for f in filenames:
            if not f.endswith('.deb'):
                continue
            if f.startswith(search_key):
                name, ver, arch = f.rstrip('.deb').split('_', 3)
                if name == package or search_key == f:
                    candidates.append((name, ver, arch))
        candidates = sort_dpkg(candidates)
        return candidates

    def formalize_package_name(self, name):
        ''' Find the latest package or check existent in Somerville Share
        '''
        try:
            if not name.endswith('.deb'):
                name = self.find_latest_package(name)
            else:
                self.package_exist(name)
        except PackageNotFoundError:
            return None
        return name


class ModaliasesService(object):
    @property
    def package_list(self):
        if hasattr(self, '_package_list'):
            return self._package_list
        try:
            url = Settings().ma_server_address + '/api/v0/deb'
            headers = {'Content-type': 'application/json',
                       'Accept': 'text/plain'}
            r = requests.get(url, headers=headers)
            data = json.loads(r.content)
            self._package_list = data['deb']
        except Exception as e:
            logging.debug('{}'.format(r.content))
            raise ModaliasesServiceError(e)
        return self._package_list

    def search_package(self, package):
        logging.info('Searching {} in MA'.format(package))
        candidates = []
        search_key = package
        if not package.endswith('.deb'):
            search_key += '_'
        for f in self.package_list:
            if not f.endswith('.deb'):
                continue
            if f.startswith(search_key):
                name, ver, arch = f.rstrip('.deb').split('_', 3)
                if name == package or search_key == f:
                    candidates.append((name, ver, arch))
        candidates = sort_dpkg(candidates)
        return candidates

    def download_package(self, filename):
        logging.info('Downloading {}'.format(filename))
        try:
            url = Settings().ma_server_address + '/api/v0/download/'
            url += filename
            r = requests.get(url)
            with open(filename, 'w+') as f:
                f.write(r.content)
        except Exception as e:
            logging.debug('{}'.format(e))
            raise DownloadError(filename)


class LocalPool(object):
    @property
    def package_list(self):
        if hasattr(self, '_package_list'):
            return self._package_list
        self._package_list = []
        if not os.path.exists(Settings().pool_path):
            return self._package_list
        for dirname, dirnames, filenames in os.walk(Settings().pool_path):
            for filename in filenames:
                if filename.endswith('.deb'):
                    self._package_list.append(filename)
        return self._package_list

    def search_package(self, package):
        logging.info('Searching {} in LocalPool'.format(package))
        candidates = []
        search_key = package
        if not package.endswith('.deb'):
            search_key += '_'
        for f in self.package_list:
            if not f.endswith('.deb'):
                continue
            if f.startswith(search_key):
                name, ver, arch = f.rstrip('.deb').split('_', 3)
                if name == package or search_key == f:
                    candidates.append((name, ver, arch))
        candidates = sort_dpkg(candidates)
        return candidates


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
    def maservice(self):
        if hasattr(self, '_maservice'):
            return self._maservice
        self._maservice = ModaliasesService()
        return self._maservice

    @property
    def localpool(self):
        if hasattr(self, '_localpool'):
            return self._localpool
        self._localpool = LocalPool()
        return self._localpool

    @property
    def base_pkgs(self):
        if hasattr(self, '_base_pkgs'):
            return self._base_pkgs
        self._base_pkgs = {}
        with open(Settings().bto_pkgs_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.endswith('.deb'):
                    name, ver, arch = line.rstrip('.deb').split('_', 3)
                    self._base_pkgs[name] = ver
                else:
                    fields = line.split()
                    self._base_pkgs[fields[0]] = fields[1]
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

    def upload_package_from_ma(self, filename):
        '''
        '''
        candidates = self.maservice.search_package(filename)
        if len(candidates) <= 0:
            raise PackageNotFoundError(filename)
        self.maservice.download_package(filename)
        logging.info('Uploading {}'.format(filename))
        self.svshare.upload_fish(filename)
        os.rename(filename, pjoin(Settings().pool_path, filename))
        return filename

    def broken_package_depends(self, package):
        dest_basepath = Settings().pool_path
        if not os.path.exists(dest_basepath):
            os.mkdir(dest_basepath)
        filename = os.path.join(dest_basepath, package)
        if not os.path.exists(filename):
            self.svshare.download_fish(package)
            os.rename(package, filename)
        return ValidateDepend(self.base_pkgs).validate(filename)

    def fix(self):
        logging.debug('fixes: ' + str(self.fixes))
        logging.debug('bugs: ' + str(self.bugs))
        logging.debug('categories: ' + str(self.categories))
        svshare = self.svshare
        fixes = self.fixes
        fixes_applied = []

        # upload
        for fix in enumerate(fixes):
            logging.info('Checking fix `{}` in somerville share'.format(fix[1]))
            fixes[fix[0]] = f = svshare.formalize_package_name(fix[1])
            if f is not None:
                continue
            logging.warn('Package `{}` not found in somerville share'.format(fix[1]))
            self.upload_package_from_ma(fix[1])

        # complete fixes with broken packages
        for fix in fixes:
            logging.info('Checking dependences `{}`'.format(fix))
            for rule in self.broken_package_depends(fix):
                logging.info('Broken rule: {}'.format(rule))
                next_rule = False
                for item in ValidateDepend.split_rule2item(rule):
                    name, op, ver = ValidateDepend.split_item(item)
                    # Somerville Share
                    for f in self.svshare.search_package(name):
                        iname, iver, iarch = f
                        if compare_dpkg_version(iver, op, ver):
                            path = '_'.join(f) + '.deb'
                            logging.info('Add package `{}` because matching rule `{}`'.format(path, rule))
                            fixes_applied.append(path)
                            next_rule = True
                            break
                    if next_rule:
                        break
                    for f in self.maservice.search_package(name):
                        iname, iver, iarch = f
                        if compare_dpkg_version(iver, op, ver):
                            path = '_'.join(f) + '.deb'
                            logging.info('Add package `{}` because matching rule `{}`'.format(path, rule))
                            logging.info('Uploading...')
                            self.upload_package_from_ma(path)
                            fixes_applied.append(path)
                            next_rule = True
                            break
                    if next_rule:
                        break
                    for f in self.localpool.search_package(name):
                        iname, iver, iarch = f
                        if compare_dpkg_version(iver, op, ver):
                            path = '_'.join(f) + '.deb'
                            realpath = os.path.join(Settings().pool_path, path)
                            r = raw_input('Find {}. Use it (Y/n)? '.format(realpath))
                            if r.lower() == 'n':
                                continue
                            shutil.copyfile(realpath, path)
                            self.svshare.upload_fish(path)
                            os.unlink(path)
                            fixes_applied.append(path)
                            next_rule = True
                    if next_rule:
                        break
                else:
                    raise BrokenDependsError('Fix `{}` dependence broken: `{}`'.format(fix, rule))
        logging.info('fixes: ' + str(self.fixes))
        logging.info('auto resolved fixes: ' + str(fixes_applied))
        logging.info('bugs: ' + str(self.bugs))
        logging.info('categories: ' + str(self.categories))
        cmd = ['fish-fix']
        for c in self.categories:
            cmd += ['-c', c]
        for c in self.fixes + fixes_applied:
            cmd += ['-f', c]
        cmd += [str(b) for b in self.bugs]
        if len(fixes_applied) > 0:
            print '!! Adding following dependence packages...'
            for f in fixes_applied:
                print '  ' + f
            r = raw_input('Continues (Y/n)? ')
            if r.lower() == 'n':
                return
        logging.debug(cmd)
        subprocess.call(cmd)
        return

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        try:
            return self.fix()
        except Exception as e:
            logging.critical(e)

    def help(self):
        print('Usage: fish-init {} [-c category] file1 [file2 ...] bug_num1 [bug_num2 ...]'.format(
              self.argv[0]))
        print '  fix bugs'

        sys.exit(0)
