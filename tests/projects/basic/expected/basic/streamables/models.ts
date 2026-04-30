// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-04-29T22:05:24.956359
import type { User } from "../accounts/models"

export interface ActorInfo {
	fullName: string;
	age: number;
	movies: Array<Movie>;
}

export interface Movie {
	uploadedBy: User;
	title: string;
	actors: Array<ActorInfo>;
}

