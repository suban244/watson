export interface Transaction {
	id: string;
	amount: number;
	title: string;
	description: string | null;
	is_expense: boolean;
	date: string;
	category: string | null;
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
}

export type TransactionUpdate = Partial<TransactionCreate>;

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
		const err = await res.text();
		throw new Error(err || `HTTP ${res.status}`);
	}
	return res.json() as Promise<T>;
}

export const listTransactions = (page = 1, size = 100): Promise<Transaction[]> =>
	request('GET', `/transactions/list/?page=${page}&size=${size}`);

export const getCategories = (): Promise<string[]> =>
	request('GET', '/transactions/categories/');

export const searchTransactions = (query: string): Promise<Transaction[]> =>
	request('POST', '/transactions/search/', { search_query: query });

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
