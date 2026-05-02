from typing import TypedDict

from ..common.types import TSExport
from ..accounts.models import User


class ActorInfo(TypedDict):
	full_name: str
	age: int
	movies: list["MovieBase"]


class MediaBase(TSExport):
	title: str
	uploaded_by: User


class MovieBase(MediaBase):
	actors: list[ActorInfo]


class ComedyMovie(MovieBase):
	how_funny: int


class DocumentaryMovie(MovieBase):
	how_serious: int


class Streamable[T: MediaBase](TSExport):
	media: T
