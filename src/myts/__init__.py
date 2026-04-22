from importlib.metadata import version

__version__ = version("myts")

from myts.core import extract_modules as extract_modules
from myts.types import MytsConfiguration as MytsConfiguration, MytsType as MytsType
from myts.decorators import myts_export as myts_export


from myts.extractors.ts import extract_ts as extract_ts
