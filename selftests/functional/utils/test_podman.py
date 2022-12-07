import os

from avocado import Test
from avocado.utils.podman import Podman


class PodmanTest(Test):
    async def test_python_version(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: dependency={"type": "podman-image", "uri": "fedora:36"}
        :avocado: tags=slow
        """
        podman = Podman()
        result = await podman.get_python_version("fedora:36")
        self.assertEqual(result, (3, 10, "/usr/bin/python3"))

    async def test_container_info(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: dependency={"type": "podman-image", "uri": "fedora:36"}
        :avocado: tags=slow
        """
        podman = Podman()
        _, stdout, _ = await podman.execute("create", "fedora:36", "/bin/bash")
        container_id = stdout.decode().strip()
        result = await podman.get_container_info(container_id)
        self.assertEqual(result["Id"], container_id)

        await podman.execute("rm", container_id)

        result = await podman.get_container_info(container_id)
        self.assertEqual(result, {})

    async def test_copy_from(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: dependency={"type": "podman-image", "uri": "fedora:36"}
        :avocado: tags=slow
        """
        podman = Podman()
        _, stdout, _ = await podman.execute("create", "fedora:36", "/bin/bash")
        container_id = stdout.decode().strip()
        await podman.copy_from_container(
            container_id, "/etc/fedora-release", self.workdir
        )
        with open(os.path.join(self.workdir, "fedora-release"), "rb") as release:
            release_content = release.read()
        self.assertEqual(release_content, b"Fedora release 36 (Thirty Six)\n")
        await podman.execute("rm", container_id)
