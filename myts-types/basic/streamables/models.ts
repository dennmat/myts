// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-02T10:20:45.168457
import type { User } from "../accounts/models";

export interface MediaBase {
	title: string;
	uploadedBy: User;
}

export interface ActorInfo {
	fullName: string;
	age: number;
	movies: Array<MovieBase>;
}

export interface MovieBase extends MediaBase {
	actors: Array<ActorInfo>;
}

export interface ComedyMovie extends MovieBase {
	howFunny: number;
}

export interface DocumentaryMovie extends MovieBase {
	howSerious: number;
}

export interface Streamable<T extends MediaBase> {
	media: T;
}

