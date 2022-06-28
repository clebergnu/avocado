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
# Copyright: Red Hat Inc. 2022
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Avocado Plugin to propagate Job results to Insights4CI
"""

from insights4ci.client.api import Insights4CIClient

from avocado.core.plugin_interfaces import CLI, ResultEvents
from avocado.core.settings import settings


class Insights4CIResultEvent(ResultEvents):

    """
    Insights4CI output class
    """

    name = 'insights4ci'
    description = 'Insights4CI result support'

    def __init__(self, config):
        self.api_client = None
        api_url = config.get('plugins.insights4ci.api_url')
        if api_url is not None:
            self.api_client = Insights4CIClient(url=api_url)

    def pre_tests(self, job):
        if self.api_client is None:
            return

    def start_test(self, result, state):
        if self.api_client is None:
            return

    def end_test(self, result, state):
        if self.api_client is None:
            return

    def test_progress(self, progress=False):
        pass

    def post_tests(self, job):
        pass


class Insights4CICLI(CLI):

    """
    Propagate Job results to Insights4CI
    """

    name = 'insights4ci'
    description = "Insights4CI options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'Insights4CI options'
        parser = run_subcommand_parser.add_argument_group(msg)
        help_msg = 'Specify the Insights4CI API url'
        settings.register_option(section='plugins.insights4ci',
                                 key='api_url',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--insights4ci-api',
                                 metavar='API_URL')


    def run(self, config):
        pass
