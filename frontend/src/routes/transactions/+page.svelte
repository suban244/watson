<script lang="ts">
	import { onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	import { getCategories, listTransactions, searchTransactions } from '$lib/api';
	import type { Transaction, TransactionGroup } from '$lib/api';
	import { formatDateLabel } from '$lib/utils/date';

	let transactions = $state<Transaction[]>([]);
	let categories = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let openIds = $state(new Set<string>());
	let selectedCategory = $state<string | null>(null);
	let searchQuery = $state('');
	let searchResults = $state<Transaction[] | null>(null);

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

	let displayedTransactions = $derived.by(() => {
		const base = searchResults ?? transactions;
		return selectedCategory ? base.filter((tx) => tx.category === selectedCategory) : base;
	});

	let totalTransactions = $derived(displayedTransactions.length);
	let totalExpenses = $derived(
		displayedTransactions.reduce((sum, tx) => sum + (tx.is_expense ? tx.amount : 0), 0)
	);

	function toggleRow(id: string) {
		const next = new Set(openIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		openIds = next;
	}

	let groupedTransactions: TransactionGroup[] = $derived.by(() => {
		const groups: Record<string, Transaction[]> = {};

		for (const transaction of displayedTransactions) {
			const date = new Date(transaction.date).toISOString().split('T')[0];
			if (!groups[date]) {
				groups[date] = [];
			}
			groups[date].push(transaction);
		}
		return Object.entries(groups).map(([date, transactions]) => ({
			label: formatDateLabel(date),
			transactions
		}));
	});

	onMount(async () => {
		try {
			[transactions, categories] = await Promise.all([listTransactions(), getCategories()]);
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

	<!-- States -->
	{#if loading}
		<p class="font-mono text-[12px] text-stone-400">Loading transactions…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-red-600">{error}</p>
	{:else}
		<!-- Filter bar -->
		<div
			class="flex flex-wrap items-center gap-2 rounded-t-[14px] border border-orange-200 bg-white px-4 py-3"
		>
			<input
				type="text"
				placeholder="Search transactions…"
				bind:value={searchQuery}
				class="min-w-[200px] flex-1 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 font-mono text-[12px] text-stone-700 placeholder-stone-400 outline-none focus:border-orange-400"
			/>
			<button
				onclick={() => (selectedCategory = null)}
				class="rounded-lg border px-3 py-2 font-mono text-[11px] font-medium transition-colors
					{selectedCategory === null
					? 'border-orange-600 bg-orange-100 text-orange-700'
					: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400'}"
			>
				All
			</button>
			{#each categories as cat}
				<button
					onclick={() => (selectedCategory = selectedCategory === cat ? null : cat)}
					class="rounded-lg border px-3 py-2 font-mono text-[11px] font-medium transition-colors
						{selectedCategory === cat
						? 'border-orange-600 bg-orange-100 text-orange-700'
						: 'border-orange-200 bg-white text-stone-600 hover:border-orange-400'}"
				>
					{cat}
				</button>
			{/each}
		</div>

		<!-- Summary bar -->
		<div
			class="flex items-center justify-between border border-t-0 border-orange-200 bg-white px-5 py-2"
		>
			<span class="font-mono text-[11px] text-stone-600">
				<strong class="text-stone-900">{totalTransactions}</strong> transactions &nbsp;·&nbsp;
				<strong class="text-red-700">-${totalExpenses.toFixed(2)}</strong> total
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
					<!-- Group header -->
					<div
						class="{gi > 0
							? 'border-t border-orange-200'
							: ''} bg-orange-50 px-5 py-3 font-mono text-[10px] font-medium tracking-widest text-stone-700 uppercase"
					>
						{group.label}
					</div>
					<!-- Rows -->
					<div class="divide-y divide-orange-100">
						{#each group.transactions as tx}
							<div class="group cursor-pointer transition-colors hover:bg-orange-50">
								<!-- Main row -->
								<div
									class="grid grid-cols-[28px_1fr_auto_auto_44px] items-center gap-2 px-5 py-3"
									onclick={() => toggleRow(tx.id)}
									role="button"
									tabindex="0"
									onkeydown={(e) => e.key === 'Enter' && toggleRow(tx.id)}
								>
									<!-- Direction -->
									<div
										class="text-center text-[13px] font-semibold {tx.is_expense
											? 'text-red-700'
											: 'text-green-700'}"
									>
										{tx.is_expense ? '↓' : '↑'}
									</div>
									<!-- Title -->
									<div class="text-[14px] font-medium text-stone-900">{tx.title}</div>
									<!-- Category badge -->
									<span
										class="inline-block rounded-full px-[9px] py-[3px] font-mono text-[10px] font-medium {tx.is_expense
											? 'bg-stone-100 text-stone-600'
											: 'bg-green-100 text-green-700'}"
									>
										{tx.category ?? '—'}
									</span>
									<!-- Amount -->
									<span
										class="text-right font-mono text-[13px] font-medium {tx.is_expense
											? 'text-red-700'
											: 'text-green-700'}"
									>
										{tx.is_expense ? '-' : '+'}${tx.amount.toFixed(2)}
									</span>
									<!-- Edit / delete (hover only) -->
									<div
										class="text-right text-[12px] text-stone-400 opacity-0 transition-opacity group-hover:opacity-100"
									>
										✏ ✕
									</div>
								</div>
								<!-- Expand: description -->
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
