# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

"""
Asset fetcher from multiple locations
"""

import errno
import hashlib
import logging
import os
import re
import shutil
import stat
import sys
import tempfile
import time

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from . import astring
from . import crypto
from . import path as utils_path
from .download import url_download
from .filelock import FileLock


# FIXME: remove
from avocado.utils.process import run

log = logging.getLogger('avocado.test')


#: The default hash algorithm to use on asset cache operations
DEFAULT_HASH_ALGORITHM = 'sha256'


class XZUncompressRetriever(object):
    '''
    This retrieves the given URL by uncompressing with xz
    '''

    def __init__(self, destination_dir=None):
        if destination_dir is None:
            destination_dir = tempfile.mkdtemp()
        self.destination_dir = destination_dir

    def action(self, spec):
        # FIXME: The origin should optionally be given, either in the
        # spec or by the pipeline runner.  This is guessing the origin
        # name from the url
        origin = os.path.join(self.destination_dir, spec.url)
        if not origin.endswith('.xz'):
            origin = "%s.xz" % origin
        if not os.path.exists(origin):
            return False

        destination = os.path.join(self.destination_dir,
                                   spec.url)
        run("xz -kfd %s" % origin)
        return True


class GzipCompressRetriever(object):
    '''
    This actually *compresses* the file given with gzip
    '''

    def __init__(self, destination_dir=None):
        if destination_dir is None:
            destination_dir = tempfile.mkdtemp()
        self.destination_dir = destination_dir

    def action(self, spec):
        # We should not play with the origin, this is just a hack
        # because we're lazy and calling gzip binary which will
        # add the .gz extension
        origin = os.path.join(self.destination_dir, spec.url)
        if origin.endswith('.gz'):
            origin = origin[:-3]
        if not os.path.exists(origin):
            return False

        destination = os.path.join(self.destination_dir,
                                   spec.url)
        # -n is needed because by default gzip will add a timestamp
        # field to the resulting gzip file, changing the file content
        # and making the expected hash fail
        run("gzip -kn %s" % origin)
        return True


class UrlRetriever(object):

    def __init__(self, destination_dir=None):
        if destination_dir is None:
            destination_dir = tempfile.mkdtemp()
        self.destination_dir = destination_dir

    def action(self, spec):
        try:
            path = os.path.join(self.destination_dir,
                                os.path.basename(spec.url))
            url_download(spec.url, path)
        except Exception:
            return False
        return True


class HashVerifier(object):

    def __init__(self, destination_dir=None):
        if destination_dir is None:
            destination_dir = tempfile.mkdtemp()
        self.destination_dir = destination_dir

    def action(self, spec):
        # this must match the place a retriever puts the file in
        path = os.path.join(self.destination_dir,
                            os.path.basename(spec.url))
        if not os.path.exists(path):
            return False
        with open(path, 'rb') as retrieved_file:
            hash_ = hashlib.new('sha1', retrieved_file.read())
            return hash_.hexdigest() == spec.expected


class AssetSpec(object):

    def __init__(self, url, expected=None, retriever=None,
                 verifier=None, parent=None, destination=None):
        self.url = url
        self.expected = expected
        self.url_parsed = urlparse.urlparse(url)
        # such as the file name of the resulting asset
        self.destination = destination
        # decide on either putting relationship in the AssetSpec themselves
        # or let it to the pipeline runner
        self.parent = parent

        if retriever is None:
            retriever = UrlRetriever
        self.retriever = retriever
        # TODO: decide on how results should be passed
        self.retriever_result = None

        if verifier is None:
            verifier = HashVerifier
        self.verifier = verifier
        # TODO: decide on how results should be passed
        self.verifier_result = None


def pipe_runner(*asset_specs):
    debug = True
    target_position = len(asset_specs)
    current_position = len(asset_specs) -1

    # FIXME, or course
    destination_dir = '/tmp'

    rock_bottom = False
    while current_position < target_position:
        asset_spec = asset_specs[current_position]
        retriever = asset_spec.retriever(destination_dir)
        verifier = asset_spec.verifier(destination_dir)

        if debug:
            print('============================================')
            print('Current position: ', current_position)
            print(' Target position: ', target_position)
            print('     Rock bottom: ', rock_bottom)
            print('  Asset Spec URL: ', asset_spec.url)
            print('============================================')

        if verifier.action(asset_spec):
            current_position += 1
            if debug:
                print('Verifier: position increment')
            continue
        else:
            retriever.action(asset_spec)
            if verifier.action(asset_spec):
                current_position += 1
                if debug:
                    print('Retrivier+Verifier: position increment')
                continue
            else:
                current_position -= 1
                if debug:
                    print('Position decrement')
                # Starting from the last step in the pipeline didn't yield any
                # benefits (there was nothing to reuse), so now there's no
                # excuse for going back again
                if current_position == 0:
                    if rock_bottom:
                        return False
                    rock_bottom = True
                continue
    return True


class UnsupportProtocolError(EnvironmentError):
    """
    Signals that the protocol of the asset URL is not supported
    """


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs,
                 expire=None):
        """
        Initialize the Asset() class.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: list of locations fetch asset from
        :param cache_dirs: list of cache directories
        :param expire: time in seconds for the asset to expire
        """
        self.name = name
        self.asset_hash = asset_hash
        if algorithm is None:
            self.algorithm = DEFAULT_HASH_ALGORITHM
        else:
            self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(self.nameobj.path)
        self.expire = expire

        #: This is a directory that lives on a cache directory, that will
        #: contain the cached files.  Its name is based on the hash of
        #: the base URL when no asset hash is given, and is an empty string
        #: (so no extra directory above the cache directory) when an asset
        #: hash is given.
        self.cache_relative_dir = None
        if self.asset_hash is None:
            base_url = "%s://%s/%s" % (self.nameobj.scheme,
                                       self.nameobj.netloc,
                                       os.path.dirname(self.nameobj.path))
            base_url_hash = hashlib.new(DEFAULT_HASH_ALGORITHM,
                                        base_url.encode(astring.ENCODING))
            self.cache_relative_dir = base_url_hash.hexdigest()
        else:
            self.cache_relative_dir = ''

    def _get_writable_cache_dir(self):
        """
        Returns the first available writable cache directory

        When a asset has to be downloaded, a writable cache directory
        is then needed. The first available writable cache directory
        will be used.
        """
        result = None
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            if utils_path.usable_rw_dir(cache_dir):
                result = cache_dir
                break
        return result

    def fetch(self):
        """
        Fetches the asset. First tries to find the asset on the provided
        cache_dirs list. Then tries to download the asset from the locations
        list provided.

        :raise EnvironmentError: When it fails to fetch the asset
        :returns: The path for the file on the cache directory.
        """
        urls = []

        # If name is actually an url, it has to be included in urls list
        if self.nameobj.scheme:
            urls.append(self.nameobj.geturl())

        # First let's search for the file in each one of the cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.cache_relative_dir,
                                           self.basename)
            self.hashfile = '%s-CHECKSUM' % self.asset_file

            # To use a cached file, it must:
            # - Exists.
            # - Be valid (not expired).
            # - Be verified (hash check).
            if (os.path.isfile(self.asset_file) and
                    not self._is_expired(self.asset_file, self.expire)):
                try:
                    with FileLock(self.asset_file, 1):
                        if self._verify():
                            return self.asset_file
                except:
                    exc_type, exc_value = sys.exc_info()[:2]
                    log.error('%s: %s' % (exc_type.__name__, exc_value))

        # If we get to this point, we have to download it from a location.
        # A writable cache directory is then needed. The first available
        # writable cache directory will be used.
        cache_dir = self._get_writable_cache_dir()
        if cache_dir is None:
            raise EnvironmentError("Can't find a writable cache directory.")

        self.asset_file = os.path.join(cache_dir, self.cache_relative_dir,
                                       self.basename)
        self.hashfile = '%s-CHECKSUM' % self.asset_file

        # Now we have a writable cache_dir. Let's get the asset.
        # Adding the user defined locations to the urls list:
        if self.locations is not None:
            for item in self.locations:
                urls.append(item)

        for url in urls:
            urlobj = urlparse.urlparse(url)
            if urlobj.scheme in ['http', 'https', 'ftp']:
                fetch = self._download
            elif urlobj.scheme == 'file':
                fetch = self._get_local_file
            else:
                raise UnsupportProtocolError("Unsupported protocol"
                                             ": %s" % urlobj.scheme)

            dirname = os.path.dirname(self.asset_file)
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            try:
                if fetch(urlobj):
                    return self.asset_file
            except:
                exc_type, exc_value = sys.exc_info()[:2]
                log.error('%s: %s' % (exc_type.__name__, exc_value))

        raise EnvironmentError("Failed to fetch %s." % self.basename)

    def _download(self, url_obj):
        try:
            # Temporary unique name to use while downloading
            temp = '%s.%s' % (self.asset_file,
                              next(tempfile._get_candidate_names()))
            url_download(url_obj.geturl(), temp)

            # Acquire lock only after download the file
            with FileLock(self.asset_file, 1):
                shutil.copy(temp, self.asset_file)
                self._compute_hash()
                return self._verify()
        finally:
            os.remove(temp)

    def _compute_hash(self):
        result = crypto.hash_file(self.asset_file, algorithm=self.algorithm)
        with open(self.hashfile, 'w') as f:
            f.write('%s %s\n' % (self.algorithm, result))

    def _get_hash_from_file(self):
        discovered = None
        if not os.path.isfile(self.hashfile):
            self._compute_hash()

        with open(self.hashfile, 'r') as hash_file:
            for line in hash_file:
                # md5 is 32 chars big and sha512 is 128 chars big.
                # others supported algorithms are between those.
                pattern = '%s [a-f0-9]{32,128}' % self.algorithm
                if re.match(pattern, line):
                    discovered = line.split()[1]
                    break
        return discovered

    def _verify(self):
        if not self.asset_hash:
            return True
        if self._get_hash_from_file() == self.asset_hash:
            return True
        else:
            return False

    def _get_local_file(self, url_obj):
        if os.path.isdir(url_obj.path):
            path = os.path.join(url_obj.path, self.name)
        else:
            path = url_obj.path

        try:
            with FileLock(self.asset_file, 1):
                try:
                    os.symlink(path, self.asset_file)
                    self._compute_hash()
                    return self._verify()
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        os.remove(self.asset_file)
                        os.symlink(path, self.asset_file)
                        self._compute_hash()
                        return self._verify()
        except:
            raise

    @staticmethod
    def _is_expired(path, expire):
        if expire is None:
            return False
        creation_time = os.lstat(path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False
