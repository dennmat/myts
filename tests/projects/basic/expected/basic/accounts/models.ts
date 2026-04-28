// AUTO-GENERATED FILE - DO NOT EDIT
// LAST GENERATED: 2026-04-27T22:01:13.760194
export type User = {
	firstName: string;
	lastName: string;
	email: string;
	uuid: string;
	signupDate: string;
};

export const AccountStatus = {
	PAST_DUE: 0,
	GOOD_STANDING: 1,
	DEACTIVATED: 2,
} as const;
export type AccountStatus = typeof AccountStatus[keyof typeof AccountStatus];

export type Account = {
	owner: User;
	status: AccountStatus;
};

export const SubscriptionPlan = {
	pro: "PRO",
	standard: "STANDARD",
	free: "FREE",
} as const;
export type SubscriptionPlan = typeof SubscriptionPlan[keyof typeof SubscriptionPlan];

export type Subscription = {
	account: Account;
	plan: SubscriptionPlan;
};

