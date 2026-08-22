<script lang="ts">
	import Modal from './Modal.svelte';
	import { clearMonthlyBudget, updateMonthlyBudget } from '$lib/api';
	import type { MonthlyBudgetStatus } from '$lib/api';

	let {
		open = $bindable(false),
		month,
		expenseCategories,
		onsaved
	}: {
		open?: boolean;
		month: MonthlyBudgetStatus;
		expenseCategories: string[];
		onsaved: (month: MonthlyBudgetStatus) => void;
	} = $props();

	// `bind:value` on <input type="number"> yields a number or null, never a string.
	let overallLimit = $state<number | null>(null);
	let limits = $state<Record<string, number | null>>({});
	let saving = $state(false);
	let resetting = $state(false);
	let confirmReset = $state(false);
	let error = $state<string | null>(null);

	/** The month's own key, so a save targets the month being viewed rather than
	 * whatever "now" is on the server. */
	let monthParam = $derived(month.month_start.slice(0, 7));

	// Every expense category gets a row, not just the budgeted ones — otherwise
	// there is no way to start budgeting a category that has no envelope yet.
	// Keys already in `limits` that are no longer valid categories still show, so
	// a stale envelope can be cleared instead of being stranded.
	let rows = $derived([
		...expenseCategories,
		...Object.keys(limits).filter((c) => !expenseCategories.includes(c))
	]);

	let spentByCategory = $derived(new Map(month.envelopes.map((e) => [e.category, e.spent])));

	let total = $derived(Object.values(limits).reduce<number>((sum, v) => sum + (v ?? 0), 0));

	function labelize(value: string): string {
		return value
			.split('_')
			.map((w) => w[0].toUpperCase() + w.slice(1))
			.join(' ');
	}

	function money(value: number): string {
		return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
	}

	$effect(() => {
		if (!open) return;
		const next: Record<string, number | null> = {};
		for (const envelope of month.envelopes) {
			// `limit === 0` is how the API reports spending in a category with no
			// envelope; that is a blank field here, not a zero limit.
			if (envelope.limit > 0) next[envelope.category] = envelope.limit;
		}
		limits = next;
		overallLimit = month.overall_limit;
		error = null;
		confirmReset = false;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = null;
		saving = true;

		try {
			const payload: Record<string, number> = {};
			for (const [category, value] of Object.entries(limits)) {
				if (value === null) continue;
				if (!Number.isFinite(value) || value < 0) {
					error = `${labelize(category)} must be a positive amount, or blank`;
					return;
				}
				// Zero and blank both mean "no envelope" — the API stores only real limits.
				if (value > 0) payload[category] = value;
			}

			if (overallLimit !== null && (!Number.isFinite(overallLimit) || overallLimit <= 0)) {
				error = 'Overall cap must be a positive amount, or blank for no cap';
				return;
			}

			// `limits` replaces the month's set wholesale, so this sends all of them.
			onsaved(
				await updateMonthlyBudget({ limits: payload, overall_limit: overallLimit }, monthParam)
			);
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save budget';
		} finally {
			saving = false;
		}
	}

	async function handleReset() {
		error = null;
		resetting = true;
		try {
			onsaved(await clearMonthlyBudget(monthParam));
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to reset budget';
		} finally {
			resetting = false;
			confirmReset = false;
		}
	}
</script>

<Modal bind:open title="Edit budget" width="max-w-[520px]">
	<form onsubmit={handleSubmit} class="flex flex-col gap-[14px]">
		<div>
			<label
				class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase"
				for="budget-overall"
			>
				Overall cap
			</label>
			<div
				class="flex items-center gap-2 rounded-lg border border-line bg-cream px-[14px] py-[6px]"
			>
				<span class="font-mono text-[18px] font-medium text-ink-3">Rs.</span>
				<input
					id="budget-overall"
					type="number"
					min="0"
					step="1"
					bind:value={overallLimit}
					placeholder="no cap"
					class="w-full bg-transparent font-mono text-[18px] font-medium text-ink outline-none"
				/>
			</div>
			<p class="mt-[5px] font-mono text-[10px] text-ink-3">
				The month's total ceiling. Independent of the envelopes below.
			</p>
		</div>

		<div>
			<div class="mb-[5px] flex items-baseline justify-between">
				<span class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Envelopes</span>
				<span class="font-mono text-[10px] text-ink-3">
					allocated <span class="text-ink-2">Rs. {money(total)}</span>
				</span>
			</div>

			<div class="overflow-hidden rounded-lg border border-line">
				{#each rows as category, i (category)}
					{@const spent = spentByCategory.get(category) ?? 0}
					<div
						class="flex items-center gap-3 px-[14px] py-[7px] {i > 0 ? 'border-t border-line' : ''}"
					>
						<label class="flex-1 text-[13px] text-ink-2" for="budget-{category}">
							{labelize(category)}
							{#if spent > 0}
								<span class="font-mono text-[10px] text-ink-3">· Rs. {money(spent)} spent</span>
							{/if}
						</label>
						<div class="flex items-center gap-[6px]">
							<span class="font-mono text-[11px] text-ink-3">Rs.</span>
							<input
								id="budget-{category}"
								type="number"
								min="0"
								step="1"
								bind:value={limits[category]}
								placeholder="—"
								class="w-[110px] rounded-lg border border-line bg-cream px-3 py-[5px] text-right font-mono text-[13px] text-ink outline-none focus:border-accent"
							/>
						</div>
					</div>
				{/each}
			</div>
			<p class="mt-[5px] font-mono text-[10px] text-ink-3">
				Leave blank to drop the envelope. Applies to this month only.
			</p>
		</div>

		{#if error}
			<p class="font-mono text-[11px] text-negative">{error}</p>
		{/if}

		<div class="mt-1 flex items-center justify-between gap-[10px]">
			{#if confirmReset}
				<button
					type="button"
					onclick={handleReset}
					disabled={resetting}
					class="cursor-pointer rounded-lg border border-negative bg-card px-3 py-[7px] text-[12px] font-semibold text-negative transition-opacity hover:opacity-90 disabled:opacity-50"
				>
					{resetting ? 'Resetting…' : 'Confirm reset'}
				</button>
			{:else}
				<button
					type="button"
					onclick={() => (confirmReset = true)}
					class="cursor-pointer rounded-lg border border-line bg-card px-3 py-[7px] text-[12px] font-medium text-ink-2 transition-colors hover:border-negative hover:text-negative"
					title="Discard this month's limits and follow the standard budget again"
				>
					Reset to standard
				</button>
			{/if}

			<div class="flex gap-[10px]">
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
					{saving ? 'Saving…' : 'Save changes'}
				</button>
			</div>
		</div>
	</form>
</Modal>
