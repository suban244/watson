<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { getBudgetOverview } from '$lib/api';
	import type { BudgetOverview, PotSummary } from '$lib/api';
	import Icon from '$lib/components/Icon.svelte';

	let overview = $state<BudgetOverview | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function money(value: number): string {
		return value.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function monthLabel(iso: string): string {
		return new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', {
			month: 'long',
			year: 'numeric'
		});
	}

	/** Null when the pot has no limit — it tracks spend without a target. */
	function progress(pot: PotSummary): number | null {
		if (!pot.limit_amount) return null;
		return pot.spent / pot.limit_amount;
	}

	function barColor(ratio: number): string {
		if (ratio > 1) return 'bg-negative';
		if (ratio >= 0.8) return 'bg-warn';
		return 'bg-accent';
	}

	onMount(async () => {
		try {
			overview = await getBudgetOverview();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load budget';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-9 py-8">
	<div class="mb-6">
		<h1 class="font-serif text-[22px] font-semibold text-ink">Budget</h1>
		<p class="mt-[3px] font-mono text-[12px] text-ink-3">Pots · spend against limits</p>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-ink-3">Loading budget…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-negative">{error}</p>
	{:else if overview}
		<!-- Monthly overview -->
		<div class="mb-6 rounded-[14px] border border-line bg-card p-5">
			<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">
				{monthLabel(overview.month.month_start)}
			</p>
			<p class="mt-2 font-mono text-[28px] font-medium text-ink">
				Rs. {money(overview.month.net_spend)}
			</p>

			{#if overview.month.excluded_spend > 0}
				<p class="mt-1 font-mono text-[11px] text-ink-2">
					Rs. {money(overview.month.gross_spend)} spent, less
					<span class="text-warn">Rs. {money(overview.month.excluded_spend)}</span>
					from pots excluded from monthly
				</p>
			{:else}
				<p class="mt-1 font-mono text-[11px] text-ink-3">total spent this month</p>
			{/if}
		</div>

		<!-- Pots -->
		{#if overview.pots.length === 0}
			<div class="rounded-[14px] border border-dashed border-line bg-card px-5 py-10 text-center">
				<p class="text-[14px] text-ink-2">No pots yet</p>
				<p class="mt-1 font-mono text-[11px] text-ink-3">
					A pot is a tag that tracks spending toward a theme — create one on the
					<a href={resolve('/tags')} class="text-accent underline">Tags</a> page.
				</p>
			</div>
		{:else}
			<div class="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
				{#each overview.pots as pot (pot.id)}
					{@const ratio = progress(pot)}
					<div class="rounded-[14px] border border-line bg-card p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<p class="truncate text-[15px] font-semibold text-ink">{pot.name}</p>
								<p class="mt-px font-mono text-[10px] text-ink-3">
									{pot.transaction_count}
									{pot.transaction_count === 1 ? 'transaction' : 'transactions'}
								</p>
							</div>
							{#if pot.exclude_from_monthly}
								<span
									class="shrink-0 rounded-full bg-warn-soft px-[9px] py-[3px] font-mono text-[9px] font-medium text-warn"
									title="This pot's spending is left out of the monthly total"
								>
									off-budget
								</span>
							{/if}
						</div>

						<p class="mt-4 font-mono text-[20px] font-medium text-ink">
							Rs. {money(pot.spent)}
						</p>

						{#if ratio === null}
							<p class="mt-1 font-mono text-[11px] text-ink-3">no limit · tracking only</p>
						{:else}
							{@const remaining = pot.limit_amount! - pot.spent}
							<p class="mt-1 font-mono text-[11px] text-ink-2">
								of Rs. {money(pot.limit_amount!)}
							</p>

							<div class="mt-3 h-2 overflow-hidden rounded-full bg-cream-2">
								<div
									class="h-full rounded-full transition-all {barColor(ratio)}"
									style="width: {Math.min(ratio, 1) * 100}%"
								></div>
							</div>

							<p class="mt-2 flex items-center gap-[5px] font-mono text-[11px]">
								{#if remaining < 0}
									<Icon name="expense" size={12} class="text-negative" />
									<span class="text-negative">Rs. {money(-remaining)} over</span>
								{:else}
									<span class="text-ink-2">Rs. {money(remaining)} left</span>
									<span class="text-ink-3">· {Math.round(ratio * 100)}% used</span>
								{/if}
							</p>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
