<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import {
		getBudgetOverview,
		getCategoryOptions,
		getMonthlyBudget,
		listTags,
		listTransactions
	} from '$lib/api';
	import type { BudgetOverview, MonthlyBudgetStatus, Tag, Transaction } from '$lib/api';
	import { toLocalDateKey } from '$lib/utils/date';
	import Icon from '$lib/components/Icon.svelte';
	import TransactionFormModal from '$lib/components/TransactionFormModal.svelte';

	const RECENT_LIMIT = 6;
	/** Enough to show the trouble spots without turning the card into a full list. */
	const AT_RISK_LIMIT = 6;

	let overview = $state<BudgetOverview | null>(null);
	let lastMonth = $state<MonthlyBudgetStatus | null>(null);
	let recent = $state<Transaction[]>([]);
	let expenseCategories = $state<string[]>([]);
	let incomeCategories = $state<string[]>([]);
	let tags = $state<Tag[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let addOpen = $state(false);

	function money(value: number): string {
		return value.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function whole(value: number): string {
		return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
	}

	function monthLabel(iso: string): string {
		return new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', {
			month: 'long',
			year: 'numeric'
		});
	}

	function shortDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function labelize(value: string): string {
		return value
			.split('_')
			.map((w) => w[0].toUpperCase() + w.slice(1))
			.join(' ');
	}

	function barColor(ratio: number): string {
		if (ratio > 1) return 'bg-negative';
		if (ratio >= 0.8) return 'bg-warn';
		return 'bg-accent';
	}

	/** Whole days from `a` to `b`, both YYYY-MM-DD, measured in UTC so a local
	 * offset cannot shift a month boundary by a day. */
	function daysBetween(a: string, b: string): number {
		return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000);
	}

	function shiftMonth(iso: string, delta: number): string {
		const [year, m] = iso.split('-').map(Number);
		const shifted = new Date(Date.UTC(year, m - 1 + delta, 1));
		return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, '0')}`;
	}

	let month = $derived(overview?.month);

	// The whole page reads `gross_spend`. The Budget page's include/exclude toggle
	// is deliberately not repeated here — its state would have nowhere to live —
	// so off-budget pot spend is stated as a footnote instead.
	let spent = $derived(month?.gross_spend ?? 0);

	let daysInMonth = $derived(month ? daysBetween(month.month_start, month.month_end) : 0);

	/** The 1st counts as one day elapsed. Clamped, so a clock sitting outside the
	 * server's month can't produce a nonsense pace. */
	let dayOfMonth = $derived(
		month && daysInMonth > 0
			? Math.min(
					Math.max(daysBetween(month.month_start, toLocalDateKey(new Date())) + 1, 1),
					daysInMonth
				)
			: 0
	);

	let monthProgress = $derived(daysInMonth > 0 ? dayOfMonth / daysInMonth : 0);

	/** Straight-line extrapolation of the run rate so far. */
	let projected = $derived(monthProgress > 0 ? spent / monthProgress : 0);

	let capRatio = $derived(month?.overall_limit ? spent / month.overall_limit : null);
	let projectedOver = $derived(month?.overall_limit ? projected - month.overall_limit : null);

	// Projection against last month's actual: both are whole-month figures, so
	// they're comparable. Comparing part-of-this-month to all-of-last would not be.
	let lastMonthSpend = $derived(lastMonth?.gross_spend ?? null);
	let vsLastMonth = $derived(
		lastMonthSpend && lastMonthSpend > 0 ? projected / lastMonthSpend - 1 : null
	);

	/** Envelopes ranked by how much of their limit is gone. Only budgeted ones —
	 * a category with no limit has nothing to be at risk against, and uncategorised
	 * spend gets its own card above. */
	let atRisk = $derived(
		(month?.envelopes ?? [])
			.filter((e) => e.limit > 0 && e.spent > 0)
			.map((e) => ({
				label: labelize(e.category),
				spent: e.spent,
				limit: e.limit,
				ratio: e.spent / e.limit
			}))
			.sort((a, b) => b.ratio - a.ratio)
			.slice(0, AT_RISK_LIMIT)
	);

	/** The 80% band rides on the percentage text, not the bar: `warn` and `accent`
	 * are only ΔE 6.4 apart, so as fills they read as the same colour. */
	function ratioTone(ratio: number): string {
		if (ratio > 1) return 'text-negative';
		if (ratio >= 0.8) return 'text-warn';
		return 'text-ink-3';
	}

	async function load() {
		const [ov, txns, categoryOptions, tagList] = await Promise.all([
			getBudgetOverview(),
			listTransactions(1, RECENT_LIMIT),
			getCategoryOptions(),
			listTags({ status: 'active' })
		]);
		overview = ov;
		recent = txns;
		expenseCategories = categoryOptions.expense;
		incomeCategories = categoryOptions.income;
		tags = tagList;

		// Dependent on the response: the server decides which month is current, so
		// "previous" is derived from what it returned rather than the browser clock.
		lastMonth = await getMonthlyBudget(shiftMonth(ov.month.month_start.slice(0, 7), -1));
	}

	onMount(async () => {
		try {
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load dashboard';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-9 py-8">
	<div class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="font-serif text-[22px] font-semibold text-ink">Dashboard</h1>
			<p class="mt-[3px] font-mono text-[12px] text-ink-3">Where the month stands</p>
		</div>
		<div class="flex flex-wrap items-center gap-3">
			{#if month}
				<a
					href={resolve('/budget')}
					class="font-mono text-[12px] text-ink-2 no-underline transition-colors hover:text-accent"
				>
					{monthLabel(month.month_start)} · view budget →
				</a>
			{/if}
			<button
				onclick={() => (addOpen = true)}
				class="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-all hover:-translate-y-px hover:opacity-90"
			>
				<Icon name="plus" />
				Add transaction
			</button>
		</div>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-ink-3">Loading dashboard…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-negative">{error}</p>
	{:else if month}
		<div class="mb-4 grid gap-4 lg:grid-cols-3">
			<!-- Headline -->
			<div class="rounded-[14px] border border-line bg-card p-5 lg:col-span-2">
				<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Spent this month</p>
				<p class="mt-2 font-mono text-[32px] leading-none font-medium text-ink">
					Rs. {money(spent)}
				</p>

				{#if month.overall_limit && capRatio !== null}
					<p class="mt-2 font-mono text-[11px] text-ink-2">
						of Rs. {money(month.overall_limit)}
						<span class="text-ink-3">· {Math.round(capRatio * 100)}% used</span>
					</p>
					<div class="mt-3 h-2 overflow-hidden rounded-full bg-cream-2">
						<div
							class="h-full rounded-full transition-all {barColor(capRatio)}"
							style="width: {Math.min(capRatio, 1) * 100}%"
						></div>
					</div>
				{:else}
					<p class="mt-2 font-mono text-[11px] text-ink-3">no overall cap set</p>
				{/if}

				<p class="mt-4 font-mono text-[11px] text-ink-3">
					{month.envelopes.filter((e) => e.spent > 0).length} categories active
					{#if month.excluded_spend > 0}
						· Rs. {whole(month.excluded_spend)} sits in off-budget pots
					{/if}
				</p>
			</div>

			<!-- Pace -->
			<div class="flex flex-col rounded-[14px] border border-line bg-card p-5">
				<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Pace</p>
				<p class="mt-2 font-mono text-[15px] font-medium text-ink">
					Day {dayOfMonth} of {daysInMonth}
				</p>

				<div class="mt-3 h-2 overflow-hidden rounded-full bg-cream-2">
					<div class="h-full rounded-full bg-ink-3" style="width: {monthProgress * 100}%"></div>
				</div>
				<p class="mt-2 font-mono text-[10px] text-ink-3">
					{Math.round(monthProgress * 100)}% of the month elapsed
				</p>

				<div class="mt-auto pt-4">
					<p class="font-mono text-[11px] text-ink-2">
						On track for <span class="text-ink">Rs. {whole(projected)}</span>
					</p>
					{#if projectedOver !== null}
						<p class="mt-[3px] flex items-center gap-[5px] font-mono text-[11px]">
							{#if projectedOver > 0}
								<Icon name="expense" size={12} class="text-negative" />
								<span class="text-negative">Rs. {whole(projectedOver)} over cap</span>
							{:else}
								<span class="text-positive">Rs. {whole(-projectedOver)} under cap</span>
							{/if}
						</p>
					{/if}
					<p class="mt-[6px] border-t border-line pt-[6px] font-mono text-[10px] text-ink-3">
						{#if lastMonthSpend === null || lastMonthSpend === 0}
							no spending last month to compare
						{:else}
							last month Rs. {whole(lastMonthSpend)}
							{#if vsLastMonth !== null}
								<span class={vsLastMonth > 0 ? 'text-negative' : 'text-positive'}>
									· {vsLastMonth > 0 ? '+' : ''}{Math.round(vsLastMonth * 100)}%
								</span>
							{/if}
						{/if}
					</p>
				</div>
			</div>
		</div>

		{#if month.uncategorized_spend > 0}
			<a
				href={resolve('/transactions')}
				class="mb-4 flex items-center gap-3 rounded-[14px] border border-dashed border-line bg-card px-5 py-3 no-underline transition-colors hover:border-accent"
			>
				<Icon name="tag" size={15} class="text-ink-3" />
				<span class="flex-1 text-[13px] text-ink-2">
					<span class="font-mono text-ink">Rs. {whole(month.uncategorized_spend)}</span> spent with no
					category this month
				</span>
				<span class="font-mono text-[11px] text-accent">categorize →</span>
			</a>
		{/if}

		<div class="grid gap-4 lg:grid-cols-3">
			<!-- Envelopes at risk -->
			<div class="rounded-[14px] border border-line bg-card p-5 lg:col-span-2">
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Envelopes at risk</p>
					<p class="font-mono text-[10px] text-ink-3">most of the limit spent first</p>
				</div>

				{#if atRisk.length === 0}
					<p class="mt-4 font-mono text-[11px] text-ink-3">
						Nothing budgeted has been spent yet this month.
					</p>
				{:else}
					<div class="mt-4 flex flex-col">
						{#each atRisk as row (row.label)}
							<div class="flex items-center gap-3 rounded px-1 py-[7px] hover:bg-cream-2">
								<span class="w-[92px] shrink-0 truncate text-[12px] text-ink-2" title={row.label}>
									{row.label}
								</span>

								<div class="h-2 flex-1 overflow-hidden rounded-full bg-cream-2">
									<!-- Clamped: past the limit the bar is simply full, and the
										 percentage carries how far past. -->
									<div
										class="h-full rounded-full transition-all {barColor(row.ratio)}"
										style="width: {Math.min(row.ratio, 1) * 100}%"
									></div>
								</div>

								<span class="w-[112px] shrink-0 text-right font-mono text-[11px] text-ink-2">
									Rs. {whole(row.spent)}
									<span class="text-ink-3">/ {whole(row.limit)}</span>
								</span>
								<span
									class="w-[38px] shrink-0 text-right font-mono text-[11px] {ratioTone(row.ratio)}"
								>
									{Math.round(row.ratio * 100)}%
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Recent activity -->
			<div class="rounded-[14px] border border-line bg-card p-5">
				<div class="flex items-baseline justify-between gap-3">
					<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Recent activity</p>
					<a
						href={resolve('/transactions')}
						class="font-mono text-[10px] text-ink-3 no-underline transition-colors hover:text-accent"
					>
						all →
					</a>
				</div>

				{#if recent.length === 0}
					<p class="mt-4 font-mono text-[11px] text-ink-3">No transactions yet.</p>
				{:else}
					<!-- Date sits under the title rather than in its own column: this card
						 is a third of the width now that the chart beside it takes two. -->
					<div class="mt-3 flex flex-col divide-y divide-line">
						{#each recent as tx (tx.id)}
							<div class="flex items-center gap-[10px] py-[9px]">
								<div class={tx.is_expense ? 'text-negative' : 'text-positive'}>
									<Icon name={tx.is_expense ? 'expense' : 'income'} size={14} strokeWidth={2.5} />
								</div>
								<div class="min-w-0 flex-1">
									<p class="truncate text-[13px] text-ink">{tx.title}</p>
									<p class="truncate font-mono text-[10px] text-ink-3">
										{shortDate(tx.date)} · {tx.category ? labelize(tx.category) : 'Uncategorized'}
									</p>
								</div>
								<span
									class="shrink-0 text-right font-mono text-[12px] font-medium {tx.is_expense
										? 'text-negative'
										: 'text-positive'}"
								>
									{tx.is_expense ? '-' : '+'}Rs. {whole(tx.amount)}
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<TransactionFormModal
	bind:open={addOpen}
	transaction={null}
	{expenseCategories}
	{incomeCategories}
	{tags}
	onsaved={() => {
		// Totals, envelopes and the breakdown all shift with a new transaction, so
		// refetch rather than splicing the row into `recent`.
		void load();
	}}
/>
