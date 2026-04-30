from typing import TypedDict

from ..common.types import TSExport
from ..accounts.models import User


class ActorInfo(TypedDict):
	full_name: str
	age: int
	movies: list["Movie"]


class Movie(TSExport):
	uploaded_by: User
	title: str
	actors: list[ActorInfo]
