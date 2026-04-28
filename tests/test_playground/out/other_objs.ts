// AUTO-GENERATED FILE - DO NOT EDIT
// LAST-GENERATED: 2026-04-22T08:59:07.518430
import type { AuthorTD, BookTD } from "./shared_types"

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

