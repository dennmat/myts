// AUTO-GENERATED FILE - DO NOT EDIT
// LAST-GENERATED: 2026-04-22T08:59:07.518253
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

