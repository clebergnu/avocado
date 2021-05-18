"""
Main entry point when called by 'python -m'.
"""

import os
import sys


# If we are running from a wheel, add the wheel to sys.path
# This allows the usage python $name.whl/module
if __package__ == "":
    # __file__ is avocado_framework*.whl/avocado/__main__.py
    # first dirname call strips of '/__main__.py', second strips off '/avocado'
    # Resulting path is the name of the wheel itself
    # Add that to sys.path so we can import pip
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)


if __name__ == '__main__':
    from avocado.core.main import main
    sys.exit(main())
