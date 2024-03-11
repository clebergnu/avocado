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
# Copyright: Red Hat Inc. 2024
# Author: Cleber Rosa <crosa@redhat.com>
"""
Handles the most basic bootstrap of components in different
environments.
"""

#: The components Avocado knows how to bootstrap, followed by the environment
#: and the actual command to be executed to have it bootstrapped
BOOTSTRAP_COMPONENTS = {
    "python": {
        "centos:stream8": "/usr/bin/dnf -y install python38 python38-setuptools",
        "ubuntu:22.04": "/bin/bash -c 'apt update && apt -y install python3 python3-setuptools'",
    }
}

class BootstrapError(Exception):
    """Generic boostrap error"""


class NoSuchComponentError(BootstrapError):
    """The component requested to be boostrapped is not known"""


class NoSuchEnvironmentCommandError(BootstrapError):
    """There is no environment command for the boostrap component requested"""


def bootstrap(component, environment, executor):
    """Bootstraps a component for a specific environment.

    The component is a generic term that users can relate to.  For
    instance, "python" means the goal of the bootstrap process is to
    have a working Python interpreter installation ready to be used.

    The executor is usually closely tied to the Avocado's task spawner
    that will be used to start a task.  A "podman executor" will
    manipulate podman images, that most probably will be started by the
    podman spawner.

    This function should return either an executor specific
    information on the result of the bootstrap process, of False if it
    failed to bootstrap the environment.

    Using the podman executor again as an example again, can return
    the "IMAGE ID" that now contains the bootstrapped environment.

    :param component: the type of software to install or setup to
                      perform in the environment
    :type component: str
    :param environment: the identification of where the component will
                        be setup on
    :trpe environment: str
    :param executor: a function that takes the environment and command,
                     knows how to run the command in the environment and
                     returns executor custom specific information
                     success, or False on failure.
    :type executor: function
    :returns: the result of the executor function
    """
    if not component in BOOTSTRAP_COMPONENTS:
        raise NoSuchComponentError(f"{component} is not known")

    environment_commands = BOOTSTRAP_COMPONENTS[component]
    if not environment in environment_commands:
        raise NoSuchEnvironmentCommandError(
            f"The steps for bootstrapping "
            "{component} in {environment} are not available"
        )

    command = environment_commands[environment]
    result = executor(environment, command)
    return result
