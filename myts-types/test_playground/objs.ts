// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-02T10:20:45.168457
export const SomeEnum = {
	ENUM1: 1,
	ENUM2: 3,
	ENUM3: 5,
} as const;
export type SomeEnum = typeof SomeEnum[keyof typeof SomeEnum];

export interface TestClassSimple {
	wow: string;
	woah: number;
}

export interface WoahAnother {
	neat: TestClassSimple;
	neaterIno: SomeEnum;
}

