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
# Copyright: Red Hat Inc. 2020
# Author: Beraldo Leal <bleal@redhat.com>

import os
from enum import Enum
from uuid import uuid4

from .dispatcher import RunnerDispatcher
from .exceptions import (JobTestSuiteReferenceResolutionError,
                         OptionValidationError)
from .parser import HintParser
from .resolver import resolve
from .settings import settings
from .tags import filter_test_tags
from .utils import resolutions_to_tasks
from .varianter import Varianter


class TestSuiteError(Exception):
    pass


class TestSuiteStatus(Enum):
    RESOLUTION_NOT_STARTED = object()
    TESTS_NOT_FOUND = object()
    TESTS_FOUND = object()
    UNKNOWN = object()


class TestSuite:
    def __init__(self, name, config=None, tests=None, job_config=None,
                 resolutions=None):
        self.name = name
        self.tests = tests
        self.resolutions = resolutions

        # Create a complete config dict with all registered options + custom
        # config
        self.config = settings.as_dict()
        if job_config:
            self.config.update(job_config)
        if config:
            self.config.update(config)

        self._variants = None
        self._references = None
        self._runner = None
        self._test_parameters = None

    def __len__(self):
        """This is a convenient method to run `len()` over this object.

        With this you can run: len(a_suite) and will return the same as
        `len(a_suite.tests)`.
        """
        return self.size

    @classmethod
    def _from_config(cls, config, name=None):
        ignore_missing = config.get('run.ignore_missing_references')
        references = config.get('run.references')
        try:
            hint = None
            hint_filepath = '.avocado.hint'
            if os.path.exists(hint_filepath):
                hint = HintParser(hint_filepath)
            resolutions = resolve(references,
                                  hint=hint,
                                  ignore_missing=ignore_missing)
        except JobTestSuiteReferenceResolutionError as details:
            raise TestSuiteError(details)

        tasks = resolutions_to_tasks(resolutions, config)

        if name is None:
            name = str(uuid4())
        return cls(name=name, config=config, tests=tasks,
                   resolutions=resolutions)

    @staticmethod
    def _increment_dict_key_counter(dict_object, key):
        try:
            dict_object[key.lower()] += 1
        except KeyError:
            dict_object[key.lower()] = 1
        return dict_object

    @property
    def references(self):
        if self._references is None:
            self._references = self.config.get('run.references')
        return self._references

    @property
    def runner(self):
        if self._runner is None:
            runner_name = self.config.get('run.test_runner') or 'nrunner'
            try:
                runner_extension = RunnerDispatcher()[runner_name]
                self._runner = runner_extension.obj
            except KeyError:
                raise TestSuiteError("Runner not implemented.")
        return self._runner

    @property
    def size(self):
        """The overall length/size of this test suite."""
        if self.tests is None:
            return 0
        return len(self.tests)

    @property
    def stats(self):
        """Return a statistics dict with the current tests."""
        stats = {}
        for test in self.tests:
            stats = self._increment_dict_key_counter(stats, test.runnable.kind)
        return stats

    @property
    def status(self):
        if self.tests is None:
            return TestSuiteStatus.RESOLUTION_NOT_STARTED
        elif self.size == 0:
            return TestSuiteStatus.TESTS_NOT_FOUND
        elif self.size > 0:
            return TestSuiteStatus.TESTS_FOUND
        else:
            return TestSuiteStatus.UNKNOWN

    @property
    def tags_stats(self):
        """Return a statistics dict with the current tests tags."""
        stats = {}
        for test in self.tests:
            if test.runnable is None:
                continue
            tags = test.runnable.tags or {}
            for tag in tags:
                stats = self._increment_dict_key_counter(stats, tag)
        return stats

    @property
    def test_parameters(self):
        """Placeholder for test parameters.

        This is related to --test-parameters command line option or
        (run.test_parameters).
        """
        if self._test_parameters is None:
            self._test_parameters = {name: value for name, value
                                     in self.config.get('run.test_parameters',
                                                        [])}
        return self._test_parameters

    @property
    def variants(self):
        if self._variants is None:
            variants = Varianter()
            if not variants.is_parsed():
                try:
                    variants.parse(self.config)
                except (IOError, ValueError) as details:
                    raise OptionValidationError("Unable to parse "
                                                "variant: %s" % details)
            self._variants = variants
        return self._variants

    def run(self, job):
        """Run this test suite with the job context in mind.

        :param job: A :class:`avocado.core.job.Job` instance.
        :rtype: set
        """
        return self.runner.run_suite(job, self)

    @classmethod
    def from_config(cls, config, name=None, job_config=None):
        """Helper method to create a TestSuite from config dicts.

        This is different from the TestSuite() initialization because here we
        are assuming that you need some help to build the test suite. Avocado
        will try to resolve tests based on the configuration information
        instead of assuming pre populated tests.

        If you need to create a custom TestSuite, please use the TestSuite()
        constructor instead of this method.

        :param config: A config dict to be used on the desired test suite.
        :type config: dict
        :param name: The name of the test suite. This is optional and default
                     is a random uuid.
        :type name: str
        :param job_config: The job config dict (a global config). Use this to
                           avoid huge configs per test suite. This is also
                           optional.
        :type job_config: dict
        """
        suite_config = config
        config = settings.as_dict()
        config.update(suite_config)
        if job_config:
            config.update(job_config)
        suite = cls._from_config(config, name)

        if not config.get('run.ignore_missing_references'):
            if not suite.tests:
                msg = ("Test Suite could not be create. No test references "
                       "provided nor any other arguments resolved into tests")
                raise TestSuiteError(msg)

        return suite
