// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT
// LAST GENERATED: 2026-04-29T22:05:24.956359
export interface User {
	firstName: string;
	lastName: string;
	email: string;
	uuid: string;
	signupDate: string;
}

export const AccountStatus = {
	PAST_DUE: 0,
	GOOD_STANDING: 1,
	DEACTIVATED: 2,
} as const;
export type AccountStatus = typeof AccountStatus[keyof typeof AccountStatus];

export interface Account {
	owner: User;
	status: AccountStatus;
}

export const SubscriptionPlan = {
	pro: "PRO",
	standard: "STANDARD",
	free: "FREE",
} as const;
export type SubscriptionPlan = typeof SubscriptionPlan[keyof typeof SubscriptionPlan];

export interface Subscription {
	account: Account;
	plan: SubscriptionPlan;
}

