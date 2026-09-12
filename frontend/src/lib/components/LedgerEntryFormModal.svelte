<script lang="ts">
	import Modal from './Modal.svelte';
	import { createLedgerEntry } from '$lib/api';
	import type { PersonBalance } from '$lib/api';
	import { toLocalDateKey } from '$lib/utils/date';
	import { BALANCE_TONES, balanceState } from '$lib/utils/ledger';

	let {
		open = $bindable(false),
		people,
		person = null,
		settle = false,
		onsaved
	}: {
		open?: boolean;
		people: PersonBalance[];
		/** Preselected person. Required when `settle` is set. */
		person?: PersonBalance | null;
		/** Record a repayment against `person`'s balance instead of a new debt. */
		settle?: boolean;
		onsaved: () => void;
	} = $props();

	let personId = $state('');
	let theyOwe = $state(true);
	let title = $state('');
	let amount = $state('');
	let date = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	function money(value: number): string {
		return value.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function describe(balance: number, nickname: string): string {
		const status = balanceState(balance);
		if (status === 'owed') return `${nickname} owes you Rs. ${money(balance)}`;
		if (status === 'owe') return `you owe ${nickname} Rs. ${money(-balance)}`;
		return 'settled up';
	}

	let selected = $derived(people.find((p) => p.id === personId) ?? null);

	/** Settling mirrors `settle` in backend/app/services/ledger.py: the sign comes
	 * from the current balance, so a repayment always moves it toward zero. */
	let signedAmount = $derived.by(() => {
		const value = Math.abs(parseFloat(amount));
		if (!Number.isFinite(value) || value === 0) return null;
		if (settle) return selected && selected.balance > 0 ? -value : value;
		return theyOwe ? value : -value;
	});

	let balanceAfter = $derived(
		selected && signedAmount !== null ? selected.balance + signedAmount : null
	);

	$effect(() => {
		if (!open) return;
		personId = person?.id ?? '';
		theyOwe = true;
		title = settle ? 'Settled up' : '';
		amount = settle && person ? Math.abs(person.balance).toFixed(2) : '';
		date = toLocalDateKey(new Date());
		error = null;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		if (!selected) {
			error = 'Pick a person';
			return;
		}
		if (!title.trim()) {
			error = 'Title is required';
			return;
		}
		if (signedAmount === null) {
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
			await createLedgerEntry(selected.id, { amount: signedAmount, title: title.trim(), date });
			onsaved();
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save entry';
		} finally {
			saving = false;
		}
	}
</script>

<Modal
	bind:open
	title={settle && person ? `Settle up with ${person.nickname}` : 'Add ledger entry'}
>
	<form onsubmit={handleSubmit} class="flex flex-col gap-[14px]">
		{#if settle}
			{#if selected}
				<div class="rounded-lg border border-line bg-cream-2 px-[14px] py-[10px]">
					<p class="text-[13px] text-ink">
						{selected.balance > 0
							? `${selected.nickname} paid you back`
							: `You paid ${selected.nickname} back`}
					</p>
					<p class="mt-px font-mono text-[11px] text-ink-3">
						Currently {describe(selected.balance, selected.nickname)}
					</p>
				</div>
			{/if}
		{:else}
			<div>
				<label
					class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
					for="ledger-person"
				>
					Person
				</label>
				<select
					id="ledger-person"
					bind:value={personId}
					class="w-full cursor-pointer rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
				>
					<option value="" disabled>Select…</option>
					{#each people as p (p.id)}
						<option value={p.id}>{p.nickname}</option>
					{/each}
				</select>
			</div>

			<div>
				<span class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase">
					Direction
				</span>
				<div class="flex overflow-hidden rounded-lg border border-line">
					<button
						type="button"
						onclick={() => (theyOwe = true)}
						class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
							{theyOwe ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
					>
						They owe me
					</button>
					<button
						type="button"
						onclick={() => (theyOwe = false)}
						class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
							{!theyOwe ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
					>
						I owe them
					</button>
				</div>
			</div>
		{/if}

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="ledger-title"
			>
				Title
			</label>
			<input
				id="ledger-title"
				type="text"
				bind:value={title}
				placeholder="e.g. Movie tickets"
				class="w-full rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
		</div>

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="ledger-amount"
			>
				Amount
			</label>
			<div
				class="flex items-center gap-2 rounded-lg border border-line bg-cream px-[14px] py-[6px]"
			>
				<span class="font-mono text-[22px] font-medium text-ink-3">Rs.</span>
				<input
					id="ledger-amount"
					type="number"
					min="0"
					step="0.01"
					bind:value={amount}
					placeholder="0.00"
					class="w-full bg-transparent font-mono text-[22px] font-medium text-ink outline-none"
				/>
			</div>
			{#if selected && balanceAfter !== null}
				<p class="mt-[6px] font-mono text-[11px] text-ink-3">
					After this:
					<span class={BALANCE_TONES[balanceState(balanceAfter)]}>
						{describe(balanceAfter, selected.nickname)}
					</span>
				</p>
			{/if}
		</div>

		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="ledger-date"
			>
				Date
			</label>
			<input
				id="ledger-date"
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
				{saving ? 'Saving…' : settle ? 'Record repayment' : 'Add entry'}
			</button>
		</div>
	</form>
</Modal>
