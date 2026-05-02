// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-02T10:20:45.168457
export interface NotADataclass<X extends Object, Y extends Object> {
	x: X;
	y: X | Y;
	z: X | Y | null;
}

export interface GenericData<T extends string | number> {
	content: NotADataclass<T, string>;
	label: string;
	test: number;
}

export interface MyOtherFakeClass {
	this: Array<number>;
	that: Array<Record<string, number>>;
	gentest: GenericData<string>;
}

export interface MyFakeBookShelf {
	books: Array<any>;
	book: any;
	author: any;
	wow: any | "wow";
	numBooks: number | null;
	cat: string | boolean | number;
	dog: number;
	someLits: "Hi" | "bye" | "no \"not\" no" | null | true | 34 | -32 | number;
}

export const ForcedEnumExport = {
	do: 1,
	it: 2,
} as const;
export type ForcedEnumExport = typeof ForcedEnumExport[keyof typeof ForcedEnumExport];

