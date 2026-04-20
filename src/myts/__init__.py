from importlib.metadata import version

__version__ = version("myts")

from myts.core import extract
from myts.types import MytsConfiguration