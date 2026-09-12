<script lang="ts">
	import Modal from './Modal.svelte';
	import Icon from './Icon.svelte';
	import { createSharedExpense } from '$lib/api';
	import type { PersonBalance } from '$lib/api';
	import { toLocalDateKey } from '$lib/utils/date';

	let {
		open = $bindable(false),
		people,
		expenseCategories,
		onsaved
	}: {
		open?: boolean;
		people: PersonBalance[];
		expenseCategories: string[];
		onsaved: () => void;
	} = $props();

	let title = $state('');
	let total = $state('');
	let date = $state('');
	let category = $state('');
	/** In the order people were picked. */
	let shares = $state<{ personId: string; amount: string }[]>([]);
	let saving = $state(false);
	let error = $state<string | null>(null);

	function money(value: number): string {
		return value.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function labelize(value: string): string {
		return value
			.split('_')
			.map((w) => w[0].toUpperCase() + w.slice(1))
			.join(' ');
	}

	function round2(value: number): number {
		return Math.round(value * 100) / 100;
	}

	let nicknames = $derived(new Map(people.map((p) => [p.id, p.nickname])));

	let parsedTotal = $derived(parseFloat(total));
	let sharesSum = $derived(shares.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0));

	/** Whatever the others don't owe is yours — that part becomes the transaction. */
	let yourShare = $derived(Number.isFinite(parsedTotal) ? round2(parsedTotal - sharesSum) : null);

	/** Even split between you and everyone picked, with the rounding remainder
	 * landing on your share. Runs when the total or the people change, so a
	 * hand-edited share only lasts until one of those does. */
	function resplit() {
		const value = parseFloat(total);
		const each = Number.isFinite(value) && value > 0 ? round2(value / (shares.length + 1)) : 0;
		shares = shares.map((s) => ({ ...s, amount: each ? each.toFixed(2) : '' }));
	}

	function togglePerson(id: string) {
		shares = shares.some((s) => s.personId === id)
			? shares.filter((s) => s.personId !== id)
			: [...shares, { personId: id, amount: '' }];
		resplit();
	}

	$effect(() => {
		if (!open) return;
		title = '';
		total = '';
		date = toLocalDateKey(new Date());
		category = '';
		shares = [];
		error = null;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		if (!title.trim()) {
			error = 'Title is required';
			return;
		}
		if (!Number.isFinite(parsedTotal) || parsedTotal <= 0) {
			error = 'Enter the bill total';
			return;
		}
		if (shares.length === 0) {
			error = 'Pick at least one person to split with';
			return;
		}
		if (shares.some((s) => !(parseFloat(s.amount) > 0))) {
			error = 'Every share needs an amount';
			return;
		}
		if (yourShare === null || yourShare < 0) {
			error = 'The shares add up to more than the bill';
			return;
		}
		if (yourShare === 0) {
			error =
				'Your share comes to Rs. 0 — if you covered someone entirely, add a ledger entry instead';
			return;
		}
		if (!date) {
			error = 'Date is required';
			return;
		}

		error = null;
		saving = true;
		try {
			await createSharedExpense({
				expense: {
					title: title.trim(),
					amount: yourShare,
					date,
					is_expense: true,
					category: category || null
				},
				shares: shares.map((s) => ({ person_id: s.personId, amount: round2(parseFloat(s.amount)) }))
			});
			onsaved();
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save shared expense';
		} finally {
			saving = false;
		}
	}
</script>

<Modal bind:open title="Split an expense" width="max-w-[460px]">
	<form onsubmit={handleSubmit} class="flex flex-col gap-[14px]">
		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="split-title"
			>
				Title
			</label>
			<input
				id="split-title"
				type="text"
				bind:value={title}
				placeholder="e.g. Dinner at Thamel"
				class="w-full rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
		</div>

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="split-total"
			>
				Bill total
			</label>
			<div
				class="flex items-center gap-2 rounded-lg border border-line bg-cream px-[14px] py-[6px]"
			>
				<span class="font-mono text-[22px] font-medium text-ink-3">Rs.</span>
				<!-- Not `bind:value`: the handler has to see the new total before it resplits. -->
				<input
					id="split-total"
					type="number"
					min="0"
					step="0.01"
					value={total}
					oninput={(e) => {
						total = e.currentTarget.value;
						resplit();
					}}
					placeholder="0.00"
					class="w-full bg-transparent font-mono text-[22px] font-medium text-ink outline-none"
				/>
			</div>
		</div>

		<div>
			<span class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase">
				Split with
			</span>
			<div class="flex flex-wrap gap-2">
				{#each people as person (person.id)}
					{@const picked = shares.some((s) => s.personId === person.id)}
					<button
						type="button"
						onclick={() => togglePerson(person.id)}
						aria-pressed={picked}
						class="flex cursor-pointer items-center gap-[5px] rounded-lg border px-3 py-[6px] font-mono text-[11px] font-medium transition-colors
							{picked
							? 'border-accent bg-accent-soft text-accent'
							: 'border-line bg-card text-ink-2 hover:border-accent'}"
					>
						{#if picked}<Icon name="check" size={11} strokeWidth={3} />{/if}
						{person.nickname}
					</button>
				{/each}
			</div>
		</div>

		{#if shares.length > 0}
			<div class="flex flex-col gap-2 rounded-lg border border-line bg-cream-2 px-[14px] py-3">
				{#each shares as share (share.personId)}
					{@const nickname = nicknames.get(share.personId) ?? 'Unknown'}
					<div class="flex items-center gap-3">
						<span class="w-28 truncate text-[13px] text-ink">{nickname} owes</span>
						<div
							class="flex flex-1 items-center gap-2 rounded-lg border border-line bg-cream px-3 py-[5px]"
						>
							<span class="font-mono text-[12px] text-ink-3">Rs.</span>
							<input
								type="number"
								min="0"
								step="0.01"
								bind:value={share.amount}
								aria-label="{nickname}'s share"
								class="w-full bg-transparent font-mono text-[13px] text-ink outline-none"
							/>
						</div>
					</div>
				{/each}
				<div
					class="mt-1 flex items-baseline justify-between border-t border-dashed border-line pt-2 font-mono text-[12px]"
				>
					<span class="text-ink-2">
						Your share <span class="text-[10px] text-ink-3">· saved as a transaction</span>
					</span>
					<span class={yourShare !== null && yourShare <= 0 ? 'text-negative' : 'text-ink'}>
						{yourShare === null ? '—' : `Rs. ${money(yourShare)}`}
					</span>
				</div>
			</div>
		{/if}

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="split-category"
			>
				Category
			</label>
			<select
				id="split-category"
				bind:value={category}
				class="w-full cursor-pointer rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			>
				<option value="">—</option>
				{#each expenseCategories as value (value)}
					<option {value}>{labelize(value)}</option>
				{/each}
			</select>
		</div>

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="split-date"
			>
				Date
			</label>
			<input
				id="split-date"
				type="date"
				bind:value={date}
				class="w-full cursor-pointer rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
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
				{saving ? 'Saving…' : 'Split expense'}
			</button>
		</div>
	</form>
</Modal>
