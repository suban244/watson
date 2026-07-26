<script lang="ts">
	import Modal from './Modal.svelte';
	import { createTransaction, updateTransaction } from '$lib/api';
	import type { Transaction } from '$lib/api';

	let {
		open = $bindable(false),
		transaction = null,
		expenseCategories,
		incomeCategories,
		onsaved
	}: {
		open?: boolean;
		transaction?: Transaction | null;
		expenseCategories: string[];
		incomeCategories: string[];
		onsaved: (tx: Transaction) => void;
	} = $props();

	let title = $state('');
	let amount = $state('');
	let date = $state('');
	let isExpense = $state(true);
	let category = $state('');
	let description = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	function labelize(value: string): string {
		return value
			.split('_')
			.map((w) => w[0].toUpperCase() + w.slice(1))
			.join(' ');
	}

	let categoryOptions = $derived(
		(isExpense ? expenseCategories : incomeCategories).map((value) => ({
			value,
			label: labelize(value)
		}))
	);

	$effect(() => {
		if (!open) return;
		title = transaction?.title ?? '';
		amount = transaction ? String(transaction.amount) : '';
		date = transaction ? transaction.date.slice(0, 10) : new Date().toISOString().slice(0, 10);
		isExpense = transaction?.is_expense ?? true;
		category = transaction?.category ?? '';
		description = transaction?.description ?? '';
		error = null;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		const parsedAmount = parseFloat(amount);
		if (!title.trim()) {
			error = 'Title is required';
			return;
		}
		if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
			error = 'Enter a valid amount';
			return;
		}
		if (!date) {
			error = 'Date is required';
			return;
		}

		error = null;
		saving = true;
		try {
			const payload = {
				title: title.trim(),
				amount: parsedAmount,
				date,
				is_expense: isExpense,
				category: category || null,
				description: description.trim() || null
			};
			const result = transaction
				? await updateTransaction(transaction.id, payload)
				: await createTransaction(payload);
			onsaved(result);
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save transaction';
		} finally {
			saving = false;
		}
	}
</script>

<Modal bind:open title={transaction ? 'Edit transaction' : 'Add transaction'}>
	<form onsubmit={handleSubmit} class="flex flex-col gap-[14px]">
		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tx-title">
				Title
			</label>
			<input
				id="tx-title"
				type="text"
				bind:value={title}
				placeholder="e.g. Grab Delivery"
				class="w-full rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
		</div>

		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tx-amount">
				Amount
			</label>
			<div class="flex items-center gap-2 rounded-lg border border-line bg-cream px-[14px] py-[6px]">
				<span class="font-mono text-[22px] font-medium text-ink-3">Rs.</span>
				<input
					id="tx-amount"
					type="number"
					min="0"
					step="0.01"
					bind:value={amount}
					placeholder="0.00"
					class="w-full bg-transparent font-mono text-[22px] font-medium text-ink outline-none"
				/>
			</div>
		</div>

		<div>
			<span class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase">Type</span>
			<div class="flex overflow-hidden rounded-lg border border-line">
				<button
					type="button"
					onclick={() => { isExpense = true; category = ''; }}
					class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
						{isExpense ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
				>
					Expense
				</button>
				<button
					type="button"
					onclick={() => { isExpense = false; category = ''; }}
					class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
						{!isExpense ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
				>
					Income
				</button>
			</div>
		</div>

		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tx-category">
				Category
			</label>
			<select
				id="tx-category"
				bind:value={category}
				class="w-full cursor-pointer rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			>
				<option value="">—</option>
				{#each categoryOptions as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		</div>

		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tx-date">
				Date
			</label>
			<input
				id="tx-date"
				type="date"
				bind:value={date}
				class="w-full cursor-pointer rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
		</div>

		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tx-description">
				Description
			</label>
			<textarea
				id="tx-description"
				bind:value={description}
				placeholder="optional…"
				rows="2"
				class="w-full resize-none rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			></textarea>
		</div>

		{#if error}
			<p class="font-mono text-[11px] text-negative">{error}</p>
		{/if}

		<div class="mt-1 flex justify-end gap-[10px]">
			<button
				type="button"
				onclick={() => (open = false)}
				class="cursor-pointer rounded-lg border border-line bg-card px-[18px] py-[9px] text-[13px] font-semibold text-ink-2 transition-opacity hover:opacity-90"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={saving}
				class="cursor-pointer rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
			>
				{saving ? 'Saving…' : transaction ? 'Save changes' : 'Add transaction'}
			</button>
		</div>
	</form>
</Modal>
