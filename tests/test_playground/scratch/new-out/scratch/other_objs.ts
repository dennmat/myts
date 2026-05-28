// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-26T21:58:10.680891
import type { AuthorTD, BookTD } from "./shared_types";

export interface NotADataclass<X, Y> {
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
	bleh: string;
	this: Array<number>;
	that: Array<Record<string, number>>;
	gentest: GenericData<string>;
}

export interface MyFakeBookShelf {
	books: Array<BookTD>;
	book: BookTD;
	author: AuthorTD;
	wow: "INT_TWO" | "wow";
	numBooks: number | null;
	cat: string | boolean | number;
	dog: number;
	someLits: "Hi" | "bye" | "no \"not\" no" | null | true | 34 | -32 | number;
}

