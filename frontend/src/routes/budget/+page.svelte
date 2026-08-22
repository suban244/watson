<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { getBudgetOverview, getCategoryOptions } from '$lib/api';
	import type { BudgetOverview, EnvelopeStatus, MonthlyBudgetStatus, PotSummary } from '$lib/api';
	import BudgetFormModal from '$lib/components/BudgetFormModal.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let overview = $state<BudgetOverview | null>(null);
	let expenseCategories = $state<string[]>([]);
	let loading = $state(true);
	let switching = $state(false);
	let error = $state<string | null>(null);
	let editOpen = $state(false);

	/** `null` means "whatever the backend calls now" — months are anchored to NPT
	 * server-side, so the browser's idea of the current month is not authoritative. */
	let monthParam = $derived(page.url.searchParams.get('month'));

	/** Guards against a slow response for an abandoned month overwriting a newer one. */
	let requestId = 0;

	// Pot spending counts toward the month by default; the toggle takes it back
	// out. Everything on the page reads the same basis so the headline and the
	// envelopes can never disagree.
	let includePots = $state(true);

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

	function envelopeSpent(envelope: EnvelopeStatus): number {
		return includePots ? envelope.spent : envelope.spent - envelope.excluded_spent;
	}

	/** Null when the pot has no limit — it tracks spend without a target. */
	function potProgress(pot: PotSummary): number | null {
		if (!pot.limit_amount) return null;
		return pot.spent / pot.limit_amount;
	}

	/** Month arithmetic in UTC on the `YYYY-MM` key, so a local timezone can never
	 * shift the 1st into the previous month. */
	function shiftMonth(iso: string, delta: number): string {
		const [year, month] = iso.split('-').map(Number);
		const shifted = new Date(Date.UTC(year, month - 1 + delta, 1));
		return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, '0')}`;
	}

	function goToMonth(target: string | null) {
		goto(resolve(target ? `/budget?month=${target}` : '/budget'), {
			keepFocus: true,
			noScroll: true
		});
	}

	function step(delta: number) {
		if (!month) return;
		goToMonth(shiftMonth(month.month_start.slice(0, 7), delta));
	}

	function applyMonth(updated: MonthlyBudgetStatus) {
		if (overview) overview = { ...overview, month: updated };
	}

	let month = $derived(overview?.month);

	let monthTotal = $derived(month ? (includePots ? month.gross_spend : month.net_spend) : 0);

	let uncategorized = $derived(
		month
			? includePots
				? month.uncategorized_spend
				: month.uncategorized_spend - month.uncategorized_excluded_spend
			: 0
	);

	// Envelopes with a limit are the budget; ones without are spending in
	// categories that were never budgeted for.
	let budgeted = $derived((month?.envelopes ?? []).filter((e) => e.limit > 0));
	let unbudgeted = $derived(
		(month?.envelopes ?? []).filter((e) => e.limit === 0 && envelopeSpent(e) > 0)
	);

	async function load(target: string | null) {
		const token = ++requestId;
		switching = true;
		try {
			const next = await getBudgetOverview(target ?? undefined);
			if (token !== requestId) return;
			overview = next;
			error = null;
		} catch (e) {
			if (token !== requestId) return;
			error = e instanceof Error ? e.message : 'Failed to load budget';
		} finally {
			if (token === requestId) {
				switching = false;
				loading = false;
			}
		}
	}

	// Refetches whenever the month in the URL changes; the reads after the first
	// `await` are untracked, so this depends on `monthParam` alone.
	$effect(() => {
		void load(monthParam);
	});

	onMount(async () => {
		expenseCategories = (await getCategoryOptions()).expense;
	});
</script>

<div class="px-9 py-8">
	<div class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="font-serif text-[22px] font-semibold text-ink">Budget</h1>
			<p class="mt-[3px] font-mono text-[12px] text-ink-3">Monthly envelopes · pots</p>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			{#if month?.source === 'override'}
				<span
					class="rounded-full bg-accent-soft px-[10px] py-[4px] font-mono text-[10px] font-medium text-accent"
					title="This month has its own limits, set apart from the standard budget"
				>
					custom limits
				</span>
			{/if}

			{#if monthParam}
				<button
					onclick={() => goToMonth(null)}
					class="cursor-pointer rounded-lg border border-line bg-card px-3 py-[7px] text-[12px] font-medium text-ink-2 transition-colors hover:border-accent hover:text-accent"
				>
					This month
				</button>
			{/if}

			<!-- Month stepper -->
			<div class="flex items-center overflow-hidden rounded-lg border border-line bg-card">
				<button
					onclick={() => step(-1)}
					disabled={!month}
					aria-label="Previous month"
					class="cursor-pointer px-[10px] py-[8px] text-ink-2 transition-colors hover:bg-cream-2 hover:text-accent disabled:opacity-40"
				>
					<Icon name="chevronLeft" size={16} />
				</button>
				<span
					class="min-w-[130px] border-x border-line px-3 py-[7px] text-center font-mono text-[12px] text-ink"
				>
					{month ? monthLabel(month.month_start) : '—'}
				</span>
				<button
					onclick={() => step(1)}
					disabled={!month}
					aria-label="Next month"
					class="cursor-pointer px-[10px] py-[8px] text-ink-2 transition-colors hover:bg-cream-2 hover:text-accent disabled:opacity-40"
				>
					<Icon name="chevronRight" size={16} />
				</button>
			</div>

			<button
				onclick={() => (editOpen = true)}
				disabled={!month}
				class="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-all hover:-translate-y-px hover:opacity-90 disabled:opacity-50"
			>
				<Icon name="edit" size={14} />
				Edit budget
			</button>
		</div>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-ink-3">Loading budget…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-negative">{error}</p>
	{:else if month}
		<!-- Dimmed rather than blanked while stepping months, so the layout holds still. -->
		<div class="transition-opacity {switching ? 'pointer-events-none opacity-40' : ''}">
			<!-- Month summary -->
			<div class="mb-6 rounded-[14px] border border-line bg-card p-5">
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Total spent</p>
						<p class="mt-2 font-mono text-[28px] font-medium text-ink">
							Rs. {money(monthTotal)}
						</p>
						{#if month.overall_limit}
							{@const ratio = monthTotal / month.overall_limit}
							<p class="mt-1 font-mono text-[11px] text-ink-2">
								of Rs. {money(month.overall_limit)}
								<span class="text-ink-3">· {Math.round(ratio * 100)}% used</span>
							</p>
							<div class="mt-3 h-2 w-[240px] max-w-full overflow-hidden rounded-full bg-cream-2">
								<div
									class="h-full rounded-full transition-all {barColor(ratio)}"
									style="width: {Math.min(ratio, 1) * 100}%"
								></div>
							</div>
						{:else}
							<p class="mt-1 font-mono text-[11px] text-ink-3">no overall cap set</p>
						{/if}
					</div>

					{#if month.excluded_spend > 0}
						<button
							onclick={() => (includePots = !includePots)}
							class="cursor-pointer rounded-lg border px-[14px] py-2 text-left text-[12px] font-medium transition-colors
							{includePots
								? 'border-line bg-card text-ink-2 hover:border-accent hover:text-accent'
								: 'border-accent bg-accent-soft text-accent'}"
						>
							{includePots ? 'Including' : 'Excluding'} off-budget pots
							<span class="mt-px block font-mono text-[10px] opacity-70">
								Rs. {money(month.excluded_spend)}
								{includePots ? 'counted' : 'hidden'}
							</span>
						</button>
					{/if}
				</div>
			</div>

			<!-- Envelopes -->
			<p class="mb-3 font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
				Envelopes
			</p>

			{#if budgeted.length === 0}
				<div
					class="mb-6 rounded-[14px] border border-dashed border-line bg-card px-5 py-10 text-center"
				>
					<p class="text-[14px] text-ink-2">No envelopes set</p>
					<p class="mt-1 font-mono text-[11px] text-ink-3">
						Give a category a limit to start budgeting this month.
					</p>
					<button
						onclick={() => (editOpen = true)}
						class="mt-4 cursor-pointer rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-opacity hover:opacity-90"
					>
						Set limits
					</button>
				</div>
			{:else}
				<div class="mb-6 overflow-hidden rounded-[14px] border border-line bg-card">
					{#each budgeted as envelope, i (envelope.category)}
						{@const spent = envelopeSpent(envelope)}
						{@const ratio = spent / envelope.limit}
						{@const remaining = envelope.limit - spent}
						<div class="px-5 py-4 {i > 0 ? 'border-t border-line' : ''}">
							<div class="flex items-baseline justify-between gap-3">
								<p class="text-[14px] font-medium text-ink">{labelize(envelope.category)}</p>
								<p class="font-mono text-[12px] text-ink-2">
									Rs. {money(spent)}
									<span class="text-ink-3">/ {money(envelope.limit)}</span>
								</p>
							</div>

							<div class="mt-[10px] h-2 overflow-hidden rounded-full bg-cream-2">
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
								{#if includePots && envelope.excluded_spent > 0}
									<span class="text-warn">
										· includes Rs. {money(envelope.excluded_spent)} from off-budget pots
									</span>
								{/if}
							</p>
						</div>
					{/each}
				</div>
			{/if}

			<!-- Spending with no envelope -->
			{#if unbudgeted.length > 0 || uncategorized > 0}
				<div class="mb-6 rounded-[14px] border border-line bg-card px-5 py-4">
					<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Not budgeted</p>
					<div class="mt-3 flex flex-col gap-2">
						{#each unbudgeted as envelope (envelope.category)}
							<div class="flex items-baseline justify-between gap-3">
								<span class="text-[13px] text-ink-2">{labelize(envelope.category)}</span>
								<span class="font-mono text-[12px] text-ink"
									>Rs. {money(envelopeSpent(envelope))}</span
								>
							</div>
						{/each}
						{#if uncategorized > 0}
							<div class="flex items-baseline justify-between gap-3">
								<span class="text-[13px] text-ink-3 italic">Uncategorized</span>
								<span class="font-mono text-[12px] text-ink">Rs. {money(uncategorized)}</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Pots -->
			<p class="mb-3 font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
				Pots <span class="font-normal tracking-normal normal-case">· all-time, not this month</span>
			</p>

			{#if overview && overview.pots.length === 0}
				<div class="rounded-[14px] border border-dashed border-line bg-card px-5 py-10 text-center">
					<p class="text-[14px] text-ink-2">No pots yet</p>
					<p class="mt-1 font-mono text-[11px] text-ink-3">
						A pot is a tag that tracks spending toward a theme — create one on the
						<a href={resolve('/tags')} class="text-accent underline">Tags</a> page.
					</p>
				</div>
			{:else if overview}
				<div class="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
					{#each overview.pots as pot (pot.id)}
						{@const ratio = potProgress(pot)}
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
		</div>
	{/if}
</div>

{#if month}
	<BudgetFormModal bind:open={editOpen} {month} {expenseCategories} onsaved={applyMonth} />
{/if}
