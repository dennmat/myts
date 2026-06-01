// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-05-31T21:59:07.932062
import type { User } from "../accounts/models";
import type { TSExport } from "../common/types";

export interface MediaBase extends TSExport {
	title: string;
	uploadedBy: User;
}

export interface ActorInfo {
	fullName: string;
	age: number;
	movies: Array<MovieBase>;
}

export interface MovieBase extends MediaBase {
	title: string;
	uploadedBy: User;
	actors: Array<ActorInfo>;
}

export interface ComedyMovie extends MovieBase {
	title: string;
	uploadedBy: User;
	actors: Array<ActorInfo>;
	howFunny: number;
}

export interface DocumentaryMovie extends MovieBase {
	title: string;
	uploadedBy: User;
	actors: Array<ActorInfo>;
	howSerious: number;
}

export interface Streamable<T extends MediaBase> extends TSExport {
	media: T;
}

