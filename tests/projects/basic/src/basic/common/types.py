from myts.decorators import myts_export
from myts.types import MytsType


@myts_export(mode="internal")
class TSExport(MytsType): ...
