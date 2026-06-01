import sys
from typing import Literal

from pydantic import BaseModel, ValidationError

from myts.config import MytsConfiguration


class TSExportConfigInput(BaseModel):
	enum_output_format: Literal["typed_const_map", "std_enum"]
	typeddict_output_format: Literal["interface", "type"]
	class_output_format: Literal["interface", "type"]
	use_declare: bool

	# type_override_map Type map? so if you see a Py MyCustomThing instead of grabbing and exporting simply use a Name specified in the map
	# it will be assumed the end user has typed this manually/separately in their TS


def default_and_merge_ts_configs(myts_config: MytsConfiguration) -> TSExportConfigInput:
	defaults = dict(
		enum_output_format="typed_const_map",
		typeddict_output_format="interface",
		class_output_format="interface",
		use_declare=True,
	)

	ts_exporter_config = myts_config.exporter.get("ts")

	if ts_exporter_config:
		defaults |= ts_exporter_config

	try:
		config = TSExportConfigInput.model_validate(ts_exporter_config)
	except ValidationError:
		print("Invalid configuration provided for ts export")
		sys.exit(65)

	return config
