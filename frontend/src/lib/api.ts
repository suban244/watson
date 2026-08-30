export interface Transaction {
	id: string;
	amount: number;
	title: string;
	description: string | null;
	is_expense: boolean;
	date: string;
	category: string | null;
	tags: string[];
	created_at: string;
	updated_at: string;
	meta: Record<string, unknown> | null;
}

export interface TransactionCreate {
	title: string;
	amount: number;
	date: string;
	is_expense: boolean;
	category?: string | null;
	description?: string | null;
	tags?: string[];
}

export type TransactionUpdate = Partial<TransactionCreate>;

/** Mirrors `MAX_TAGS_PER_TRANSACTION` in backend/app/services/tags.py. */
export const MAX_TAGS_PER_TRANSACTION = 5;

export type TagStatus = 'active' | 'archived';

export interface Tag {
	id: string;
	slug: string;
	name: string;
	description: string | null;
	is_pot: boolean;
	/** Only meaningful when `is_pot`; the backend rejects them otherwise. */
	exclude_from_monthly: boolean;
	limit_amount: number | null;
	status: TagStatus;
}

export interface TagCreate {
	name: string;
	/** Derived from `name` when omitted. Immutable once the tag exists. */
	slug?: string | null;
	description?: string | null;
	is_pot?: boolean;
	exclude_from_monthly?: boolean;
	limit_amount?: number | null;
}

/** `slug` and `status` are absent by design — slugs are immutable, and status
 * moves through archive/restore. */
export type TagUpdate = Partial<Omit<TagCreate, 'slug'>>;

const BASE = '/api/v1';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const opts: RequestInit = {
		method,
		headers: { 'Content-Type': 'application/json' }
	};
	if (body !== undefined) opts.body = JSON.stringify(body);

	const res = await fetch(`${BASE}${path}`, opts);
	if (res.status === 204) return null as T;
	if (!res.ok) {
		const body = await res.text();
		// FastAPI wraps errors as {"detail": ...}; the tag/transaction services write
		// those strings to be shown to the user verbatim, so unwrap rather than dump JSON.
		let message = body;
		try {
			const detail = JSON.parse(body)?.detail;
			if (typeof detail === 'string') message = detail;
			else if (Array.isArray(detail)) message = detail.map((d) => d.msg ?? String(d)).join(', ');
		} catch {
			// not JSON — fall back to the raw body
		}
		throw new Error(message || `HTTP ${res.status}`);
	}
	return res.json() as Promise<T>;
}

export interface TransactionFilters {
	categories?: string[];
	tags?: string[];
	date_from?: string;
	date_to?: string;
	month?: string; // YYYY-MM, prefer this over date_from/date_to when present
	is_expense?: boolean;
	amount_min?: number;
	amount_max?: number;
}

export const listTransactions = (
	page = 1,
	size = 500,
	filters: TransactionFilters = {}
): Promise<Transaction[]> => {
	const params = new URLSearchParams({ page: String(page), size: String(size) });
	for (const [key, value] of Object.entries(filters)) {
		if (value === undefined) continue;
		if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
		else params.set(key, String(value));
	}
	return request('GET', `/transactions/list/?${params}`);
};

export const getCategories = (): Promise<string[]> =>
	request('GET', '/transactions/categories/');

export interface CategoryOptions {
	expense: string[];
	income: string[];
}

export const getCategoryOptions = (): Promise<CategoryOptions> =>
	request('GET', '/transactions/categories/options/');

export const searchTransactions = (query: string, page = 1, size = 500): Promise<Transaction[]> => {
	const params = new URLSearchParams({ page: String(page), size: String(size) });
	return request('POST', `/transactions/search/?${params}`, { search_query: query });
};

export const getTransaction = (id: string): Promise<Transaction> =>
	request('GET', `/transactions/${id}/`);

export const createTransaction = (data: TransactionCreate): Promise<Transaction> =>
	request('POST', '/transactions/', data);

export const updateTransaction = (id: string, data: TransactionUpdate): Promise<Transaction> =>
	request('PATCH', `/transactions/${id}/`, data);

export const deleteTransaction = (id: string): Promise<null> =>
	request('DELETE', `/transactions/${id}/`);

export interface TransactionGroup {
	label: string;
	transactions: Transaction[];
}

/** A pot plus its all-time spend. `limit_amount` may be null — the pot then
 * tracks spend without a target. */
export interface PotSummary extends Tag {
	spent: number;
	transaction_count: number;
}

export interface EnvelopeStatus {
	category: string;
	limit: number;
	spent: number;
	/** The part of `spent` carried by pots flagged `exclude_from_monthly`. */
	excluded_spent: number;
}

export interface MonthlyBudgetStatus {
	month_start: string;
	/** Exclusive. */
	month_end: string;
	source: 'standard' | 'override';

	gross_spend: number;
	excluded_spend: number;
	net_spend: number;

	uncategorized_spend: number;
	uncategorized_excluded_spend: number;

	overall_limit: number | null;
	envelopes: EnvelopeStatus[];
}

export interface BudgetOverview {
	pots: PotSummary[];
	month: MonthlyBudgetStatus;
}

export interface MonthlyBudgetUpdate {
	limits?: Record<string, number>;
	overall_limit?: number | null;
}

const monthQuery = (month?: string) => (month ? `?month=${month}` : '');

export const getBudgetOverview = (month?: string): Promise<BudgetOverview> =>
	request('GET', `/budget/overview/${monthQuery(month)}`);

export const getMonthlyBudget = (month?: string): Promise<MonthlyBudgetStatus> =>
	request('GET', `/budget/monthly/${monthQuery(month)}`);

export const updateMonthlyBudget = (
	data: MonthlyBudgetUpdate,
	month?: string
): Promise<MonthlyBudgetStatus> => request('PATCH', `/budget/monthly/${monthQuery(month)}`, data);

/** Drop the month's override so it follows the standard budget again. */
export const clearMonthlyBudget = (month?: string): Promise<MonthlyBudgetStatus> =>
	request('DELETE', `/budget/monthly/${monthQuery(month)}`);

export const listTags = (opts: { status?: TagStatus; is_pot?: boolean } = {}): Promise<Tag[]> => {
	const params = new URLSearchParams();
	if (opts.status) params.set('status', opts.status);
	if (opts.is_pot !== undefined) params.set('is_pot', String(opts.is_pot));
	const query = params.toString();
	return request('GET', `/tags/list/${query ? `?${query}` : ''}`);
};

export const createTag = (data: TagCreate): Promise<Tag> => request('POST', '/tags/', data);

export const updateTag = (id: string, data: TagUpdate): Promise<Tag> =>
	request('PATCH', `/tags/${id}/`, data);

export const archiveTag = (id: string): Promise<Tag> => request('POST', `/tags/${id}/archive/`);

export const restoreTag = (id: string): Promise<Tag> => request('POST', `/tags/${id}/restore/`);

/** Rejected with 409 while the tag is still on a transaction — archive instead. */
export const deleteTag = (id: string): Promise<null> => request('DELETE', `/tags/${id}/`);
