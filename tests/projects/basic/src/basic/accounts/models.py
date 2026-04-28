import datetime
import enum
import uuid

from myts import MytsType


# Keep as direct export from MytsType vs the fake projects inherited convenience one
class User(MytsType):
	first_name: str
	last_name: str
	email: str
	uuid: uuid.UUID
	signup_date: datetime.datetime


class AccountStatus(enum.IntEnum):
	PAST_DUE = 0
	GOOD_STANDING = 1
	DEACTIVATED = 2


class Account(MytsType):
	owner: User
	status: AccountStatus


class SubscriptionPlan(enum.Enum):
	pro = "PRO"
	standard = "STANDARD"
	free = "FREE"


class Subscription(MytsType):
	account: Account
	plan: SubscriptionPlan
