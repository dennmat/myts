
# Myts

## Warning: v0.1.0 this is not production ready

Converts MyPy types to TS types.

Uses MyPy's internal api to gather type info.

Call as a cli, optionally directory watchable.
Or import and invoke directly from you Python code.

## Installation

-- If you're somehow reading this right now, it's not on PyPI yet, working on it.

**pip**
```sh
pip install myts
```

**poetry**
```sh
poetry add myts
```


## Usage

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