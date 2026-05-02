from myts.decorators import myts_export
from myts.types import MytsType


class NotIncluded: ...


@myts_export(mode="internal")
class TSExport(MytsType): ...
