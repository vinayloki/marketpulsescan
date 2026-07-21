"""Entrypoint for python -m marketpulse"""

import sys

from marketpulse.cli import main

if __name__ == "__main__":
    sys.exit(main())
