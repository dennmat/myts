## Usage

Python (Mypy)

```python
class SomeEnum(IntEnum):
	A = 5
	B = 6
	C = 12

class MyTypedDict(TypedDict):
	a: NotRequired[str]
	b: Literal["one", "two", "three"]

@dataclass
class Example(MytsType):
	something: str
	otherthing: "OtherThing"

@dataclass
class OtherThing(MytsType):
	thing: SomeEnum
	info: MyTypedDict
```

Output (Typescript)

```typescript
export enum SomeEnum {
	A = 5,
	B = 6,
	C = 12
}

export type MyTypedDict = {
	a?: string;
	b: "one" | "two" | "three"
};

export type Example = {
	something: string;
	otherthing: OtherThing;
};

export type OtherThing = {
	thing: SomeEnum;
	info: MyTypedDict;
};
```