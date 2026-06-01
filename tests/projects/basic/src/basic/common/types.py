from myts import myts_export, MytsType


class NotIncluded: ...


@myts_export(mode="internal")
class TSExport(MytsType): ...
