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
# Copyright: Red Hat Inc. 2025
# Authors: Cleber Rosa <crosa@redhat.com>

from avocado.core import varianter
from avocado.core.plugin_interfaces import CLI, Init, Varianter
from avocado.core.settings import settings
from avocado.core.tree import TreeNode


class LoopVariantsInit(Init):

    name = "loop_variants"
    description = "Python Dictionary based varianter"

    def initialize(self):
        help_msg = "The number of times to run each test"
        settings.register_option(
            section="run",
            key="loop_variants",
            default=0,
            key_type=int,
            help_msg=help_msg,
        )


class LoopVariantsCLI(CLI):
    """
    Loop based Varianter options
    """

    name = "loop variants"
    description = "Loop based Varianter options for the 'run' subcommand"

    def configure(self, parser):
        for name in ("run", "variants"):  # intentionally omitting "multiplex"
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            sparser = subparser.add_argument_group(
                "Loop based varianter options"
            )
            settings.add_argparser_to_option(
                namespace="run.loop_variants",
                parser=sparser,
                long_arg="--loop",
                metavar="NUMBER_OF_RUNS",
                allow_multiple=True
            )

    def run(self, config):
        pass


class LoopVariants(Varianter):
    """
    Applies a number of runs using the variants mechanism
    """

    name = "loop_variants"
    description = "Loop based varianter with unchanged variants"

    def initialize(self, config):
        # pylint: disable=W0201
        self.variants = config.get("run.loop_variants")

    def __iter__(self):
        if self.variants is None:
            return

        for vid in range(1, self.variants + 1):
            yield {
                "variant_id": f"{vid}",
                "variant": [TreeNode("", {})],
                "paths": ["/"],
            }

    def __len__(self):
        return self.variants

    def to_str(self, summary, variants, **kwargs):
        """
        Return human readable representation

        The summary/variants accepts verbosity where 0 means silent and
        maximum is up to the plugin.

        :param summary: How verbose summary to output (int)
        :param variants: How verbose list of variants to output (int)
        :param kwargs: Other free-form arguments
        :rtype: str
        """
        if not self.variants:
            return ""
        out = []

        if variants:
            # variants == 0 means disable, but in plugin it's brief
            out.append(f"Dict Variants ({len(self)}):")
            for variant in self:
                out.extend(
                    varianter.variant_to_str(variant, variants - 1, kwargs, False)
                )
        return "\n".join(out)
