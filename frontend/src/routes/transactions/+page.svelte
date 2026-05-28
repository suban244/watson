<script lang="ts">
	import { onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	import { getCategories, listTransactions, searchTransactions } from '$lib/api';
	import type { Transaction, TransactionGroup } from '$lib/api';
	import { formatDateLabel } from '$lib/utils/date';

	// --- data ---
	let transactions = $state<Transaction[]>([]);
	let categories = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// --- filters ---
	let searchQuery = $state('');
	let searchResults = $state<Transaction[] | null>(null);

	let selectedCategories = $state(new Set<string>());
	let categoryOpen = $state(false);

	let dateFrom = $state('');
	let dateTo = $state('');
	let dateRangeOpen = $state(false);

	let amountMin = $state('');
	let amountMax = $state('');
	let amountOpen = $state(false);

	// --- row UI ---
	let openIds = $state(new Set<string>());

	// TODO: hybrid fetching — apply filters client-side instantly, then re-fetch from backend
	// in the background with the same filters and replace results when the response arrives.

	// --- derived ---
	let displayedTransactions = $derived.by(() => {
		const base = searchResults ?? transactions;
		let r = selectedCategories.size > 0
			? base.filter((tx) => tx.category !== null && selectedCategories.has(tx.category))
			: [...base];
		if (dateFrom) r = r.filter((tx) => tx.date.slice(0, 10) >= dateFrom);
		if (dateTo) r = r.filter((tx) => tx.date.slice(0, 10) <= dateTo);
		if (amountMin) r = r.filter((tx) => tx.amount >= parseFloat(amountMin));
		if (amountMax) r = r.filter((tx) => tx.amount <= parseFloat(amountMax));
		return r;
	});

	let totalTransactions = $derived(displayedTransactions.length);
	let totalExpenses = $derived(
		displayedTransactions.reduce((sum, tx) => sum + (tx.is_expense ? tx.amount : 0), 0)
	);

	let hasActiveFilters = $derived(
		selectedCategories.size > 0 || !!dateFrom || !!dateTo || !!amountMin || !!amountMax
	);

	let groupedTransactions: TransactionGroup[] = $derived.by(() => {
		const groups: Record<string, Transaction[]> = {};
		for (const transaction of displayedTransactions) {
			const date = new Date(transaction.date).toISOString().split('T')[0];
			if (!groups[date]) groups[date] = [];
			groups[date].push(transaction);
		}
		return Object.entries(groups).map(([date, transactions]) => ({
			label: formatDateLabel(date),
			transactions
		}));
	});

	// --- effects ---
	$effect(() => {
		const q = searchQuery.trim();
		if (!q) {
			searchResults = null;
			return;
		}
		const timer = setTimeout(async () => {
			searchResults = await searchTransactions(q);
		}, 300);
		return () => clearTimeout(timer);
	});

	// --- functions ---
	function setAmountPreset(min: string, max: string) {
		amountMin = min;
		amountMax = max;
	}

	function formatAmountChip(min: string, max: string): string {
		if (min && max) return `Rs. ${min} – Rs. ${max}`;
		if (min) return `> Rs. ${min}`;
		return `< Rs. ${max}`;
	}

	function setDatePreset(preset: 'last7d' | 'last30d' | 'thisMonth' | 'lastMonth' | 'last3m' | 'thisYear') {
		const now = new Date();
		const today = now.toISOString().split('T')[0];
		const ago = (days: number) => {
			const d = new Date(now);
			d.setDate(d.getDate() - days);
			return d.toISOString().split('T')[0];
		};
		if (preset === 'last7d')    { dateFrom = ago(6);  dateTo = today; }
		if (preset === 'last30d')   { dateFrom = ago(29); dateTo = today; }
		if (preset === 'thisMonth') {
			dateFrom = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
			dateTo = today;
		}
		if (preset === 'lastMonth') {
			dateFrom = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
			dateTo = new Date(now.getFullYear(), now.getMonth(), 0).toISOString().split('T')[0];
		}
		if (preset === 'last3m')    { dateFrom = ago(89); dateTo = today; }
		if (preset === 'thisYear')  { dateFrom = `${now.getFullYear()}-01-01`; dateTo = today; }
	}

	function formatDateChip(from: string, to: string): string {
		const fmt = (s: string) =>
			new Date(s + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		if (from && to) return `${fmt(from)} – ${fmt(to)}`;
		if (from) return `From ${fmt(from)}`;
		return `To ${fmt(to)}`;
	}

	function clearAll() {
		selectedCategories = new Set();
		dateFrom = '';
		dateTo = '';
		amountMin = '';
		amountMax = '';
		searchQuery = '';
	}

	function toggleRow(id: string) {
		const next = new Set(openIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		openIds = next;
	}

	onMount(async () => {
		try {
			[transactions, categories] = await Promise.all([listTransactions(1, 500), getCategories()]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load transactions';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-9 py-8">
	<!-- Page header -->
	<div class="mb-6 flex items-end justify-between">
		<div>
			<h1 class="font-serif text-[22px] font-semibold text-stone-900">Transactions</h1>
			<p class="mt-[3px] font-mono text-[12px] text-stone-400">All activity · newest first</p>
		</div>
		<div class="flex gap-2">
			<button
				class="cursor-pointer rounded-lg border border-orange-200 bg-white px-[18px] py-[9px] text-[13px] font-semibold text-stone-600 transition-all hover:-translate-y-px hover:opacity-90"
			>
				↓ Import
			</button>
			<button
				class="cursor-pointer rounded-lg bg-orange-600 px-[18px] py-[9px] text-[13px] font-semibold text-white transition-all hover:-translate-y-px hover:opacity-90"
			>
				+ Add
			</button>
		</div>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-stone-400">Loading transactions…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-red-600">{error}</p>
	{:else}
		<!-- Filter bar -->
		<div class="rounded-t-[14px] border border-orange-200 bg-white">
			<div class="flex flex-wrap items-center gap-[10px] p-4">
				<!-- Search -->
				<div
					class="flex min-w-[200px] flex-1 items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-[14px] py-2"
				>
					<span class="text-[14px] opacity-40">🔍</span>
					<input
						type="text"
						placeholder="Search description…"
						bind:value={searchQuery}
						class="flex-1 bg-transparent font-mono text-[12px] text-stone-700 placeholder-stone-400 outline-none"
					/>
				</div>

				<!-- Category pill -->
				<button
					onclick={() => { categoryOpen = !categoryOpen; dateRangeOpen = false; amountOpen = false; }}
					class="cursor-pointer rounded-lg border px-[14px] py-2 text-[12px] font-medium transition-colors
						{categoryOpen || selectedCategories.size > 0
						? 'border-orange-600 bg-orange-100 text-orange-600'
						: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400 hover:text-orange-600'}"
				>
					Category ▾
				</button>

				<!-- Date range pill -->
				<button
					onclick={() => { dateRangeOpen = !dateRangeOpen; categoryOpen = false; }}
					class="cursor-pointer rounded-lg border px-[14px] py-2 text-[12px] font-medium transition-colors
						{dateRangeOpen || dateFrom || dateTo
						? 'border-orange-600 bg-orange-100 text-orange-600'
						: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400 hover:text-orange-600'}"
				>
					Date range ▾
				</button>

				<!-- Amount pill -->
				<button
					onclick={() => { amountOpen = !amountOpen; categoryOpen = false; dateRangeOpen = false; }}
					class="cursor-pointer rounded-lg border px-[14px] py-2 text-[12px] font-medium transition-colors
						{amountOpen || amountMin || amountMax
						? 'border-orange-600 bg-orange-100 text-orange-600'
						: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400 hover:text-orange-600'}"
				>
					Amount ▾
				</button>
			</div>
			{#if categoryOpen}
				<div
					class="flex flex-wrap gap-2 border-t border-orange-100 px-4 py-3"
					transition:slide={{ duration: 150 }}
				>
					<button
						onclick={() => (selectedCategories = new Set())}
						class="cursor-pointer rounded-lg border px-3 py-[6px] font-mono text-[11px] font-medium transition-colors
							{selectedCategories.size === 0
							? 'border-orange-600 bg-orange-100 text-orange-600'
							: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400'}"
					>
						All
					</button>
					{#each categories as cat}
						<button
							onclick={() => {
								const next = new Set(selectedCategories);
								if (next.has(cat)) next.delete(cat);
								else next.add(cat);
								selectedCategories = next;
							}}
							class="cursor-pointer rounded-lg border px-3 py-[6px] font-mono text-[11px] font-medium transition-colors
								{selectedCategories.has(cat)
								? 'border-orange-600 bg-orange-100 text-orange-600'
								: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400'}"
						>
							{cat}
						</button>
					{/each}
				</div>
			{/if}

			{#if amountOpen}
				<div
					class="flex flex-col gap-3 border-t border-orange-100 px-4 py-3"
					transition:slide={{ duration: 150 }}
				>
					<!-- Presets -->
					<div class="flex flex-wrap gap-2">
						{#each [
							{ label: '< Rs. 100',              min: '',     max: '100'  },
							{ label: '< Rs. 500',              min: '',     max: '500'  },
							{ label: 'Rs. 500 – Rs. 2,000',   min: '500',  max: '2000' },
							{ label: '> Rs. 2,000',            min: '2000', max: ''     },
						] as preset}
							<button
								onclick={() => setAmountPreset(preset.min, preset.max)}
								class="cursor-pointer rounded-lg border border-orange-200 bg-white px-3 py-[5px] font-mono text-[11px] text-stone-600 transition-colors hover:border-orange-400 hover:text-orange-600"
							>
								{preset.label}
							</button>
						{/each}
					</div>
					<!-- Custom range -->
					<div class="flex items-center gap-3">
						<span class="font-mono text-[9px] uppercase tracking-widest text-stone-400">Min Rs.</span>
						<input
							type="number"
							min="0"
							placeholder="0"
							bind:value={amountMin}
							class="w-24 rounded-lg border border-orange-200 bg-orange-50 px-3 py-[6px] font-mono text-[12px] text-stone-700 outline-none focus:border-orange-400"
						/>
						<span class="font-mono text-[9px] uppercase tracking-widest text-stone-400">Max Rs.</span>
						<input
							type="number"
							min="0"
							placeholder="∞"
							bind:value={amountMax}
							class="w-24 rounded-lg border border-orange-200 bg-orange-50 px-3 py-[6px] font-mono text-[12px] text-stone-700 outline-none focus:border-orange-400"
						/>
					</div>
				</div>
			{/if}

			{#if dateRangeOpen}
				<div
					class="flex flex-col gap-3 border-t border-orange-100 px-4 py-3"
					transition:slide={{ duration: 150 }}
				>
					<!-- Presets -->
					<div class="flex flex-wrap gap-2">
						{#each [
							{ key: 'last7d',    label: 'Last 7d' },
							{ key: 'last30d',   label: 'Last 30d' },
							{ key: 'thisMonth', label: 'This month' },
							{ key: 'lastMonth', label: 'Last month' },
							{ key: 'last3m',    label: 'Last 3 months' },
							{ key: 'thisYear',  label: 'This year' },
						] as preset}
							<button
								onclick={() => setDatePreset(preset.key as Parameters<typeof setDatePreset>[0])}
								class="cursor-pointer rounded-lg border border-orange-200 bg-white px-3 py-[5px] font-mono text-[11px] text-stone-600 transition-colors hover:border-orange-400 hover:text-orange-600"
							>
								{preset.label}
							</button>
						{/each}
					</div>
					<!-- Custom range -->
					<div class="flex items-center gap-3">
						<span class="font-mono text-[9px] uppercase tracking-widest text-stone-400">From</span>
						<input
							type="date"
							bind:value={dateFrom}
							class="cursor-pointer rounded-lg border border-orange-200 bg-orange-50 px-3 py-[6px] font-mono text-[12px] text-stone-700 outline-none focus:border-orange-400"
						/>
						<span class="font-mono text-[9px] uppercase tracking-widest text-stone-400">To</span>
						<input
							type="date"
							bind:value={dateTo}
							class="cursor-pointer rounded-lg border border-orange-200 bg-orange-50 px-3 py-[6px] font-mono text-[12px] text-stone-700 outline-none focus:border-orange-400"
						/>
					</div>
				</div>
			{/if}

			{#if hasActiveFilters}
				<div
					class="flex flex-wrap items-center gap-2 border-t border-orange-100 px-4 py-3"
					transition:slide={{ duration: 150 }}
				>
					<span class="font-mono text-[9px] uppercase tracking-widest text-stone-400">Active:</span>
					{#each selectedCategories as cat}
						<span class="inline-flex items-center gap-[5px] rounded-full bg-stone-900 py-[3px] pl-3 pr-[6px] font-mono text-[10px] text-white">
							{cat}
							<button
								onclick={() => {
									const next = new Set(selectedCategories);
									next.delete(cat);
									selectedCategories = next;
								}}
								class="cursor-pointer border-none bg-transparent text-[11px] leading-none text-white/70 hover:text-white"
							>✕</button>
						</span>
					{/each}
					{#if amountMin || amountMax}
						<span class="inline-flex items-center gap-[5px] rounded-full bg-stone-900 py-[3px] pl-3 pr-[6px] font-mono text-[10px] text-white">
							{formatAmountChip(amountMin, amountMax)}
							<button
								onclick={() => { amountMin = ''; amountMax = ''; }}
								class="cursor-pointer border-none bg-transparent text-[11px] leading-none text-white/70 hover:text-white"
							>✕</button>
						</span>
					{/if}
					{#if dateFrom || dateTo}
						<span class="inline-flex items-center gap-[5px] rounded-full bg-stone-900 py-[3px] pl-3 pr-[6px] font-mono text-[10px] text-white">
							{formatDateChip(dateFrom, dateTo)}
							<button
								onclick={() => { dateFrom = ''; dateTo = ''; }}
								class="cursor-pointer border-none bg-transparent text-[11px] leading-none text-white/70 hover:text-white"
							>✕</button>
						</span>
					{/if}
					<button
						onclick={clearAll}
						class="cursor-pointer rounded-lg border border-orange-200 bg-white px-[10px] py-[3px] text-[11px] font-medium text-stone-600 transition-colors hover:border-orange-400"
					>
						Clear all
					</button>
				</div>
			{/if}
		</div>

		<!-- Summary bar -->
		<div
			class="flex items-center justify-between border border-t-0 border-orange-200 bg-white px-5 py-2"
		>
			<span class="font-mono text-[11px] text-stone-600">
				<strong class="text-stone-900">{totalTransactions}</strong> transactions &nbsp;·&nbsp;
				<strong class="text-red-700">-Rs. {totalExpenses.toFixed(2)}</strong> total
			</span>
			<span class="font-mono text-[10px] text-stone-400">newest first</span>
		</div>

		<!-- Transaction list -->
		<div
			class="overflow-hidden rounded-b-[14px] border border-t-0 border-orange-200 bg-white shadow-sm"
		>
			{#if groupedTransactions.length === 0}
				<p class="px-5 py-10 text-center font-mono text-[12px] text-stone-400">
					No transactions yet
				</p>
			{:else}
				{#each groupedTransactions as group, gi}
					<div
						class="{gi > 0
							? 'border-t border-orange-200'
							: ''} bg-orange-50 px-5 py-3 font-mono text-[10px] font-medium tracking-widest text-stone-700 uppercase"
					>
						{group.label}
					</div>
					<div class="divide-y divide-orange-100">
						{#each group.transactions as tx}
							<div class="group cursor-pointer transition-colors hover:bg-orange-50">
								<div
									class="grid grid-cols-[28px_1fr_auto_auto_44px] items-center gap-2 px-5 py-3"
									onclick={() => toggleRow(tx.id)}
									role="button"
									tabindex="0"
									onkeydown={(e) => e.key === 'Enter' && toggleRow(tx.id)}
								>
									<div
										class="text-center text-[13px] font-semibold {tx.is_expense
											? 'text-red-700'
											: 'text-green-700'}"
									>
										{tx.is_expense ? '↓' : '↑'}
									</div>
									<div class="text-[14px] font-medium text-stone-900">{tx.title}</div>
									<span
										class="inline-block rounded-full px-[9px] py-[3px] font-mono text-[10px] font-medium {tx.is_expense
											? 'bg-stone-100 text-stone-600'
											: 'bg-green-100 text-green-700'}"
									>
										{tx.category ?? '—'}
									</span>
									<span
										class="text-right font-mono text-[13px] font-medium {tx.is_expense
											? 'text-red-700'
											: 'text-green-700'}"
									>
										{tx.is_expense ? '-' : '+'}Rs. {tx.amount.toFixed(2)}
									</span>
									<div
										class="text-right text-[12px] text-stone-400 opacity-0 transition-opacity group-hover:opacity-100"
									>
										✏ ✕
									</div>
								</div>
								{#if openIds.has(tx.id)}
									<div
										class="border-t border-dashed border-orange-200 bg-orange-50 px-5 pt-[10px] pb-3 pl-[56px]"
										transition:slide={{ duration: 200 }}
									>
										<div class="flex items-start gap-3">
											<span
												class="w-20 shrink-0 pt-[2px] font-mono text-[9px] tracking-widest text-stone-400 uppercase"
												>Description</span
											>
											<span class="text-[13px] text-stone-500 italic">
												{tx.description ?? 'No description'}
											</span>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>
