from mytsold.decorators import myts_export
from mytsold.types import MytsType


class NotIncluded: ...


@myts_export(mode="internal")
class TSExport(MytsType): ...
