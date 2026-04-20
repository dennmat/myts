
# Myts

<!--![myts logo](assets/logo.png)-->

## Warning: v0.1.0 this is not production ready

Converts MyPy types to TS types. Uses MyPy's internal api to gather type info.

Call as a cli, optionally directory watchable.
Or import and invoke directly from your Python code.

## Installation

**pip**
```sh
pip install myts
```

**poetry**
```sh
poetry add myts
```


## Usage

### In your code

Myts looks for any classes that inherit from `MytsType` to start building its dependency graph.
These by default will be included in the output TS.

Alternatively you can use the `myts_export` decorator on `Enum`s and `TypedDict`s and `class`es that you would like to have exported without needing to be referenced by a `MytsType` class.

**Note**: Right now you cannot alias either of these, in a future version that will be okay.

```python
from enum import IntEnum
from myts import MytsType, myts_export

@myts_export
class Fruit(IntEnum): # Will be in the TS output
	apple = 0
	orange = 1
	banana = 2

class Vegetable(IntEnum): # Will not be, because it is not referenced ever and is not decorated with myts_export
	carrot = 0
	celery = 1
	lettuce = 2

class Drink(IntEnum): # Will be in the output, reference by a MytsType below
	water = 0
	milk = 1
	soda = 2

class BeveragePreference(MytsType): # Will export and will also export the Drink enum
	drink: Drink
	person: Person
```


### CLI

To see all __cli__ options run 

```sh
myts -h
```

#### Simplest example

To generate the `.ts` files. 

```sh
cd <myprojectroot>
myts --output your/output/dir/
```
### 

#### A more complex example

Uses `trim-root` to remove a common `py` module path from the output.

Uses `watch` to automatically update generated `ts` when the `py` changes.

```sh
cd <myprojectroot>
myts --output your/output/dir/ -w
```


### Py

```python
import pathlib
import myts

config = myts.MytsConfiguration(
	root=pathlib.Path('someprojdir'), # defaults to os.cwd()
	output=pathlib.Path('someoutputdir'),
	group='module', # 'single' or 'module' - single will output a single .ts file, 'module' will output files matching the `py` files they come from
	preserve_structure=True, # No effect if group == 'single', otherwise determines output structure. If true folders will be created to match py paths
	dry_run=False, # If true, just prints the paths of output files that would be written
	output_file_name='types.ts', # Only used if group == 'single', determines the name of the single file generated
	trim_root="myapp.some.path" # When preserving structure, use this to trim a common root 
)

myts.export(config)
```

## Roadmap

- [x] Export to multiple files, flat folder or matching py module structure
- [x] Support generics
- [x] Watch for `py` changes and auto generate `ts`
- [ ] Export enum literal references preserved. I.e. `myvar: Literal[MyEnum.VAL]` should export as `myvar: MyEnum.VAL`
- [ ] Config options for 
  - [ ] [Py api] override output names of vars and files
  - [ ] Variable and type naming options (camelCase, PascalCase, snake_case)
  - [ ] Interface vs type output
- [ ] `myts_export` params to override naming and module grouping
- [ ] Name overwriting using meta class on `MytsType` or params to `myts_export`

## Example of functionality
Python (Mypy)

```python
from myts import MytsType, myts_export

@myts_export # Flags for export even though it is never referenced
class MyNotReferencedEnum(StrEnum):
	A = "🍁"
	B = "🐝"
	C = "👀"

class SomeEnum(IntEnum): # Automatically exported due to being reference by OtherThing
	A = 5
	B = 6
	C = 12

class MyTypedDict[T](TypedDict): # Generics supported
	a: NotRequired[T]
	b: Literal["one", "two", "three"]

class Example(MytsType): # Inherits MytsType -- will be exported
	something: str
	other_thing: "OtherThing"

@dataclass
class OtherThing(MytsType):
	thing: SomeEnum
	info: MyTypedDict
```

Output (Typescript)

```typescript
export enum MyNotReferencedEnum {
	A = "🍁",
	B = "🐝",
	C = "👀",
}

export enum SomeEnum {
	A = 5,
	B = 6,
	C = 12,
}

export type MyTypedDict<T> = {
	a?: T;
	b: "one" | "two" | "three";
};

export type Example = {
	something: string;
	otherThing: OtherThing;
};

export type OtherThing = {
	thing: SomeEnum;
	info: MyTypedDict;
};
```