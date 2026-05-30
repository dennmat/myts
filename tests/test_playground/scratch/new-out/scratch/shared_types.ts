// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-30T09:45:09.970815
export const FakeStrEnum = {
	STRING_ONE: "string",
	STRING_TWO: "string2",
	STRING_THREE: "3",
} as const;
export type FakeStrEnum = typeof FakeStrEnum[keyof typeof FakeStrEnum];

export interface AuthorTD {
	firstName: string;
	lastName: string;
	age: number;
	city: FakeStrEnum;
}

export const FakeIntEnum = {
	INT_ONE: 0,
	INT_TWO: 1,
	INT_THREE: 2,
} as const;
export type FakeIntEnum = typeof FakeIntEnum[keyof typeof FakeIntEnum];

export interface BookTD {
	author: AuthorTD;
	name: string;
	isbn: string;
	genre: FakeIntEnum;
}

