import time

from avocado import Test


class FastTest(Test):

    """
    Fastest possible test

    :avocado: tag=fast
    """

    def test(self):
        pass


class SlowTest(Test):

    """
    Slow test

    :avocado: tag=slow
    """
    def test(self):
        time.sleep(3)
