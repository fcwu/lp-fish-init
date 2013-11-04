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

## TEST cases
# [O] f only in SShare if and only if f is FISH tarball
# [O] f only in SShare if and only if f is deb
# [O] f only in MA
# [O] f only in local (pool)
# [O] f only in local (pwd)
# [O] f depends broken
# [?] f depends broken, dependance in MA
# [O] f depends broken, dependance in local
# [O] f depends broken, and not found

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
    f = {}
    f['<'] = f['<<'] = f['lt'] = lambda score: score < 0
    f['<='] = f['le'] = lambda score: score <= 0
    f['='] = f['eq'] = lambda score: score == 0
    f['>='] = f['ge'] = lambda score: score >= 0
    f['>'] = f['>>'] = f['ge'] = lambda score: score > 0
    try:
        return f[op](compare_result)
    except:
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

    def file_exist(self, filename):
        filenames = self.list(pjoin('pool', filename[0]))
        for f in filenames:
            if f == filename:
                return True
        raise PackageNotFoundError(filename)

    def search_package(self, package):
        logging.info('Searching {} in SomervilleShare'.format(package))
        filenames = self.list(pjoin('pool', package[0]))
        search_key = package
        candidates = []
        if not search_key.endswith('.deb'):
            search_key += '_'
        #logging.debug('In pool {}: {}'.format(search_key, filenames))
        for f in filenames:
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
            if not name.endswith('.deb') and not name.endswith('.tar.gz'):
                name = self.find_latest_package(name)
            else:
                self.file_exist(name)
        except PackageNotFoundError:
            return None
        return name

    def match_package(self, name, op, ver):
        for f in self.search_package(name):
            iname, iver, iarch = f
            if compare_dpkg_version(iver, op, ver):
                return '_'.join(f) + '.deb'
        return None


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

    def match_package(self, name, op, ver):
        for f in self.search_package(name):
            iname, iver, iarch = f
            if compare_dpkg_version(iver, op, ver):
                return '_'.join(f) + '.deb'
        return None


class LocalPool(object):
    @property
    def pools(self):
        dirs = ['.']
        if os.path.exists(Settings().pool_path):
            dirs.append(Settings().pool_path)
        return dirs

    @property
    def package_list(self):
        def iterate_dir(path):
            for dirname, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.deb'):
                        self._package_list.append(filename)

        self._package_list = []
        map(iterate_dir, self.pools)
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

    def realpath(self, package):
        for basedir in ('./', Settings().pool_path):
            path = pjoin(basedir, package)
            if os.path.exists(path):
                return os.path.normpath(path)
        raise PackageNotFoundError(package)

    def match_package(self, name, op, ver):
        for f in self.search_package(name):
            iname, iver, iarch = f
            if compare_dpkg_version(iver, op, ver):
                return '_'.join(f) + '.deb'
        return None


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
    def dry_run(self):
        if hasattr(self, '_dry_run'):
            return self._dry_run
        self._prepare_arguments()
        return self._dry_run

    @property
    def fixes_broken(self):
        if hasattr(self, '_fixes_broken'):
            return self._fixes_broken
        return []

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
        self._dry_run = False
        skip = 0
        parameters = self.argv[1:]
        for arg in enumerate(parameters):
            if skip > 0:
                skip -= 1
                continue
            if arg[1] == '-c':
                skip = 1
                self._categories.append(parameters[arg[0] + 1])
                continue
            if arg[1] == '-f':
                skip = 1
                self._fixes.append(parameters[arg[0] + 1])
                continue
            if arg[1] == '-n':
                self._dry_run = True
                continue
            try:
                self._bugs.append(int(arg[1]))
            except ValueError:
                self._fixes.append(arg[1])

    def upload_package(self, f):
        if self.upload_package_from_ma(f):
            return True
        if self.upload_package_from_local(f):
            return True
        return False

    def upload_package_from_local(self, filename):
        candidates = self.localpool.search_package(filename)
        if len(candidates) <= 0:
            return False
        realpath = self.localpool.realpath(filename)
        if realpath != filename:
            shutil.copyfile(realpath, filename)
        logging.info('Uploading {}'.format(filename))
        self.svshare.upload_fish(filename)
        if realpath != filename:
            os.unlink(filename)
        return filename

    def upload_package_from_ma(self, filename):
        candidates = self.maservice.search_package(filename)
        if len(candidates) <= 0:
            return False
        self.maservice.download_package(filename)
        logging.info('Uploading {}'.format(filename))
        self.svshare.upload_fish(filename)
        dest = pjoin(Settings().pool_path, filename)
        if not os.path.exists(dest):
            os.makedirs(Settings().pool_path)
        os.rename(filename, dest)
        return filename

    def broken_depends(self, package):
        dest_basepath = Settings().pool_path
        if not os.path.exists(dest_basepath):
            os.mkdir(dest_basepath)
        filename = os.path.join(dest_basepath, package)
        if not os.path.exists(filename):
            self.svshare.download_fish(package)
            os.rename(package, filename)
        return ValidateDepend(self.base_pkgs).validate(filename)

    def fix_broken_depends(self, fix, rule):
        fixes = []
        for item in ValidateDepend.split_rule2item(rule):
            name, op, ver = ValidateDepend.split_item(item)
            path = self.svshare.match_package(name, op, ver)
            if path is not None:
                logging.info('Add package "{}" because matching rule "{}"'.
                             format(path, rule))
                fixes.append(path)
                break
            path = self.maservice.match_package(name, op, ver)
            if path is not None:
                logging.info('Add package "{}" because matching rule "{}"'.
                             format(path, rule))
                self.upload_package_from_ma(path)
                fixes.append(path)
                break
            path = self.localpool.match_package(name, op, ver)
            if path is not None:
                r = raw_input('Find {}. Use it (Y/n)? '.format(path))
                if r.lower() == 'n':
                    continue
                self.upload_package_from_local(path)
                fixes.append(path)
                break
        else:
            raise BrokenDependsError('Fix "{}" dependence broken: "{}"'.
                                     format(fix, rule))
        return fixes

    def fix_commit(self):
        fixes_resolved = self.fixes_broken
        logging.info('fixes: ' + str(self.fixes))
        logging.info('fixes automatically resolved: ' + str(fixes_resolved))
        logging.info('bugs: ' + str(self.bugs))
        logging.info('categories: ' + str(self.categories))
        if len(fixes_resolved) > 0:
            print '!! Adding following dependence packages...'
            for f in fixes_resolved:
                print '  ' + f
            r = raw_input('Continues (Y/n)? ')
            if r.lower() == 'n':
                return
        cmd = ['fish-fix-noupload']
        for c in self.categories:
            cmd += ['-c', c]
        for c in self.fixes + fixes_resolved:
            cmd += ['-f', c]
        cmd += [str(b) for b in self.bugs]
        logging.debug(cmd)
        if not self.dry_run:
            subprocess.call(cmd)

    def fix(self):
        logging.debug('fixes: ' + str(self.fixes))
        logging.debug('bugs: ' + str(self.bugs))
        logging.debug('categories: ' + str(self.categories))
        svshare = self.svshare
        fixes = self.fixes

        # upload
        for fix in enumerate(fixes):
            logging.info('Checking fix `{}` in SomervilleShare'.format(fix[1]))
            f = svshare.formalize_package_name(fix[1])
            if f is not None:
                fixes[fix[0]] = f
                continue
            logging.warn('Package "{}" not found in SomervilleShare'.
                         format(fix[1]))
            if not self.upload_package(fix[1]):
                raise PackageNotFoundError(fix[1])

        # complete fixes with broken packages
        self._fixes_broken = []
        for fix in fixes:
            if not fix.endswith('.deb'):
                continue
            logging.info('Checking dependences `{}`'.format(fix))
            for rule in self.broken_depends(fix):
                logging.info('Broken rule: {}'.format(rule))
                self._fixes_broken += self.fix_broken_depends(fix, rule)

        self.fix_commit()
        return

    def run(self, argv):
        self.argv = argv
        if argv[0] == 'help':
            self.help()
            return
        try:
            if len(self.bugs) <= 0:
                self.help()
                return
            return self.fix()
        except Exception as e:
            logging.critical(e)

    def help(self):
        print('Usage: fish-init {} [-n] [-c category] file1 [file2 ...] '
              'bug_num1 [bug_num2 ...]'.format(
              self.argv[0]))
        print '  fix bugs'
        print 'Options:'
        print '  -n: dry run'

        sys.exit(0)
