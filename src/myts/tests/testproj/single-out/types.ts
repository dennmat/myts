// AUTO-GENERATED FILE - DO NOT EDIT
// LAST-GENERATED: 2026-04-22T21:54:32.490865
export type TestClassSimple = {
	wow: string;
	woah: number;
};

export const SomeEnum = {
	ENUM1: 1,
	ENUM2: 3,
	ENUM3: 5,
} as const;
export type SomeEnum = typeof SomeEnum[keyof typeof SomeEnum];

export type WoahAnother = {
	neat: TestClassSimple;
	neaterIno: SomeEnum;
};

export type NotADataclass<X, Y> = {
	x: X;
	y: X | Y;
	z: X | Y | null;
};

export type GenericData<T> = {
	content: NotADataclass<T, string>;
	label: string;
	test: number;
};

export type MyOtherFakeClass = {
	this: Array<number>;
	that: Array<Record<string, number>>;
	gentest: GenericData<string>;
};

export type MyFakeBookShelf = {
	books: Array<BookTD>;
	book: BookTD;
	author: AuthorTD;
	wow: "INT_TWO" | "wow";
	numBooks: number | null;
	cat: string | boolean | number;
	dog: number;
	someLits: "Hi" | "bye" | "no \"not\" no" | null | true | 34 | -32 | number;
};

export const ForcedEnumExport = {
	do: 1,
	it: 2,
} as const;
export type ForcedEnumExport = typeof ForcedEnumExport[keyof typeof ForcedEnumExport];

export const FakeIntEnum = {
	INT_ONE: 0,
	INT_TWO: 1,
	INT_THREE: 2,
} as const;
export type FakeIntEnum = typeof FakeIntEnum[keyof typeof FakeIntEnum];

export const FakeStrEnum = {
	STRING_ONE: "string",
	STRING_TWO: "string2",
	STRING_THREE: "3",
} as const;
export type FakeStrEnum = typeof FakeStrEnum[keyof typeof FakeStrEnum];

export type AuthorTD = {
	firstName: string;
	lastName: string;
	age: number;
	city: FakeStrEnum;
};

export type BookTD = {
	author: AuthorTD;
	name: string;
	isbn: string;
	genre: FakeIntEnum;
};

