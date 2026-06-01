// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-31T21:29:46.874301
import type { AuthorTD, BookTD } from "./shared_types";

export interface NotADataclass<X, Y> {
	x: X;
	y: X | Y;
	z: X | Y | null;
}

export const EnumFlag = {
	FLAG1: 1,
	FLAG2: 2,
	FLAG3: 3,
} as const;
export type EnumFlag = typeof EnumFlag[keyof typeof EnumFlag];

export interface GenericData<T extends string | number> {
	content: NotADataclass<T, string>;
	label: string;
	test: number;
	flag: EnumFlag;
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
	numBooks: number;
	cat: string | boolean | number;
	dog: number;
	someLits: "Hi" | "bye" | "no \"not\" no" | null | true | 34 | -32 | number;
}

