// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-06-01T22:26:21.914547
export declare type OtherUnion = 4 | 3;

export declare type MyUnion = "cat" | 5 | OtherUnion | null;

export interface TestClassSimple {
	wow: string;
	woah: number;
	cool: MyUnion;
}

export const SomeEnum = {
	ENUM1: 1,
	ENUM2: 3,
	ENUMB: 4,
	ENUM3: 5,
	ENUMA: 6,
} as const;
export type SomeEnum = typeof SomeEnum[keyof typeof SomeEnum];

export interface WoahAnother {
	neat: TestClassSimple;
	neaterIno: SomeEnum;
}

export declare type MyGenericAlias<T> = Array<T> | Record<string, T>;

export interface UseMyGeneric<X> {
	stillGeneric: MyGenericAlias<X>;
	lessGeneric: MyGenericAlias<number>;
}

