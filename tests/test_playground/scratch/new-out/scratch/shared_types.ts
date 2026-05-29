// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-28T22:00:58.405681
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

export interface AuthorTD {
	firstName: string;
	lastName: string;
	age: number;
	city: FakeStrEnum;
}

export interface BookTD {
	author: AuthorTD;
	name: string;
	isbn: string;
	genre: FakeIntEnum;
}

