/** Below this, a balance is float noise from uneven splits — call it settled. */
const EPSILON = 0.005;

/** `owed`: they owe you. `owe`: you owe them. */
export type BalanceState = 'owed' | 'owe' | 'settled';

export function balanceState(balance: number): BalanceState {
	if (balance > EPSILON) return 'owed';
	if (balance < -EPSILON) return 'owe';
	return 'settled';
}

export const BALANCE_TONES: Record<BalanceState, string> = {
	owed: 'text-positive',
	owe: 'text-negative',
	settled: 'text-ink-3'
};
