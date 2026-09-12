<script lang="ts">
	import { onMount } from 'svelte';
	import {
		deleteLedgerEntry,
		getCategoryOptions,
		getLedgerBalances,
		listLedgerEntries
	} from '$lib/api';
	import type { LedgerEntry, PersonBalance } from '$lib/api';
	import { formatDateLabel, toLocalDateKey } from '$lib/utils/date';
	import { BALANCE_TONES, balanceState } from '$lib/utils/ledger';
	import ConfirmModal from '$lib/components/ConfirmModal.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import IconButton from '$lib/components/IconButton.svelte';
	import LedgerEntryFormModal from '$lib/components/LedgerEntryFormModal.svelte';
	import SharedExpenseModal from '$lib/components/SharedExpenseModal.svelte';

	/** The API's cap; the list says so when it's hit rather than looking complete. */
	const ENTRY_LIMIT = 500;

	let balances = $state<PersonBalance[]>([]);
	let entries = $state<LedgerEntry[]>([]);
	let expenseCategories = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let entriesLoading = $state(false);
	let entriesError = $state<string | null>(null);

	let selectedPersonId = $state<string | null>(null);

	let entryModalOpen = $state(false);
	let settleMode = $state(false);
	let modalPerson = $state<PersonBalance | null>(null);
	let splitModalOpen = $state(false);
	let confirmOpen = $state(false);
	let deletingEntry = $state<LedgerEntry | null>(null);

	/** Guards against a slow response for an abandoned filter overwriting a newer one. */
	let requestId = 0;

	function money(value: number): string {
		return value.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function signed(value: number): string {
		return `${value >= 0 ? '+' : '−'}Rs. ${money(Math.abs(value))}`;
	}

	let peopleById = $derived(new Map(balances.map((p) => [p.id, p])));
	let selectedPerson = $derived(
		selectedPersonId ? (peopleById.get(selectedPersonId) ?? null) : null
	);

	let owedToYou = $derived(balances.reduce((sum, p) => sum + Math.max(p.balance, 0), 0));
	let youOwe = $derived(balances.reduce((sum, p) => sum + Math.max(-p.balance, 0), 0));
	let net = $derived(owedToYou - youOwe);

	// Open balances first, biggest first; settled people keep the backend's
	// nickname order below them (sort is stable).
	let sortedBalances = $derived(
		[...balances].sort((a, b) => {
			const aOpen = balanceState(a.balance) !== 'settled';
			const bOpen = balanceState(b.balance) !== 'settled';
			if (aOpen !== bOpen) return aOpen ? -1 : 1;
			return aOpen ? Math.abs(b.balance) - Math.abs(a.balance) : 0;
		})
	);

	// The API already returns newest first, and date keys aren't integer-like, so
	// the object keeps insertion order.
	let groupedEntries = $derived.by(() => {
		const groups: Record<string, LedgerEntry[]> = {};
		for (const entry of entries) {
			const key = toLocalDateKey(entry.date);
			if (!groups[key]) groups[key] = [];
			groups[key].push(entry);
		}
		return Object.entries(groups).map(([key, rows]) => ({
			key,
			label: formatDateLabel(key),
			rows
		}));
	});

	async function loadEntries(personId: string | null) {
		const token = ++requestId;
		entriesLoading = true;
		try {
			const rows = await listLedgerEntries(personId ?? undefined, ENTRY_LIMIT);
			if (token !== requestId) return;
			entries = rows;
			entriesError = null;
		} catch (e) {
			if (token === requestId) {
				entriesError = e instanceof Error ? e.message : 'Failed to load entries';
			}
		} finally {
			if (token === requestId) entriesLoading = false;
		}
	}

	/** Balances are summed server-side, so every change re-reads them rather
	 * than patching the numbers locally. */
	async function refresh() {
		void loadEntries(selectedPersonId);
		try {
			balances = await getLedgerBalances();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load balances';
		}
	}

	function selectPerson(id: string | null) {
		selectedPersonId = selectedPersonId === id ? null : id;
		void loadEntries(selectedPersonId);
	}

	function openEntryModal(person: PersonBalance | null) {
		modalPerson = person;
		settleMode = false;
		entryModalOpen = true;
	}

	function openSettleModal(person: PersonBalance) {
		modalPerson = person;
		settleMode = true;
		entryModalOpen = true;
	}

	function openDeleteConfirm(entry: LedgerEntry) {
		deletingEntry = entry;
		confirmOpen = true;
	}

	onMount(async () => {
		try {
			let options;
			[balances, entries, options] = await Promise.all([
				getLedgerBalances(),
				listLedgerEntries(undefined, ENTRY_LIMIT),
				getCategoryOptions()
			]);
			expenseCategories = options.expense;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load ledger';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-9 py-8">
	<div class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="font-serif text-[22px] font-semibold text-ink">Ledger</h1>
			<p class="mt-[3px] font-mono text-[12px] text-ink-3">Who owes whom · newest first</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={() => (splitModalOpen = true)}
				disabled={balances.length === 0}
				class="flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-card px-[18px] py-[9px] text-[13px] font-semibold text-ink-2 transition-all hover:-translate-y-px hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
			>
				<Icon name="users" />
				Split expense
			</button>
			<button
				onclick={() => openEntryModal(selectedPerson)}
				disabled={balances.length === 0}
				class="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-all hover:-translate-y-px hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
			>
				<Icon name="plus" />
				Add entry
			</button>
		</div>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-ink-3">Loading ledger…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-negative">{error}</p>
	{:else}
		<!-- Summary -->
		<div
			class="mb-6 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5 rounded-[14px] border border-line bg-card p-5"
		>
			<div>
				<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Owed to you</p>
				<p class="mt-2 font-mono text-[24px] font-medium text-positive">Rs. {money(owedToYou)}</p>
			</div>
			<div>
				<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">You owe</p>
				<p class="mt-2 font-mono text-[24px] font-medium text-negative">Rs. {money(youOwe)}</p>
			</div>
			<div>
				<p class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Net</p>
				<p class="mt-2 font-mono text-[24px] font-medium {BALANCE_TONES[balanceState(net)]}">
					{balanceState(net) === 'settled' ? 'Rs. 0.00' : signed(net)}
				</p>
				<p class="mt-1 font-mono text-[11px] text-ink-3">
					{#if balanceState(net) === 'owed'}in your favour{:else if balanceState(net) === 'owe'}against
						you{:else}all square{/if}
				</p>
			</div>
		</div>

		<!-- People -->
		<p class="mb-3 font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
			People <span class="font-normal tracking-normal normal-case">· click one to filter</span>
		</p>

		{#if balances.length === 0}
			<div
				class="mb-6 rounded-[14px] border border-dashed border-line bg-card px-5 py-10 text-center"
			>
				<p class="text-[14px] text-ink-2">No people yet</p>
				<p class="mt-1 font-mono text-[11px] text-ink-3">
					Ask Watson to add someone, then track what you owe each other here.
				</p>
			</div>
		{:else}
			<div class="mb-6 grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
				{#each sortedBalances as person (person.id)}
					{@const status = balanceState(person.balance)}
					{@const active = selectedPersonId === person.id}
					<div
						onclick={() => selectPerson(person.id)}
						onkeydown={(e) =>
							e.key === 'Enter' && e.target === e.currentTarget && selectPerson(person.id)}
						role="button"
						tabindex="0"
						aria-pressed={active}
						class="cursor-pointer rounded-[14px] border p-5 transition-colors
							{active ? 'border-accent bg-accent-soft' : 'border-line bg-card hover:border-accent'}"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<p class="truncate text-[15px] font-semibold text-ink">{person.nickname}</p>
								<p class="mt-px truncate font-mono text-[10px] text-ink-3">
									{person.full_name ? `${person.full_name} · ` : ''}{person.entry_count}
									{person.entry_count === 1 ? 'entry' : 'entries'}
								</p>
							</div>
							{#if status !== 'settled'}
								<button
									onclick={(e) => {
										e.stopPropagation();
										openSettleModal(person);
									}}
									class="shrink-0 cursor-pointer rounded-lg border border-line bg-card px-[10px] py-[4px] text-[11px] font-medium text-ink-2 transition-colors hover:border-accent hover:text-accent"
								>
									Settle up
								</button>
							{/if}
						</div>

						<p class="mt-4 font-mono text-[20px] font-medium {BALANCE_TONES[status]}">
							Rs. {money(status === 'settled' ? 0 : Math.abs(person.balance))}
						</p>
						<p class="mt-1 font-mono text-[11px] text-ink-2">
							{#if status === 'owed'}owes you{:else if status === 'owe'}you owe{:else}settled up{/if}
						</p>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Entries -->
		<div class="mb-3 flex items-center gap-2">
			<p class="font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
				Entries
			</p>
			{#if selectedPerson}
				<span
					class="inline-flex items-center gap-[5px] rounded-full bg-ink py-[3px] pr-[6px] pl-3 font-mono text-[10px] text-white"
				>
					{selectedPerson.nickname}
					<button
						onclick={() => selectPerson(null)}
						aria-label="Show everyone"
						class="flex cursor-pointer items-center border-none bg-transparent leading-none text-white/70 hover:text-white"
						><Icon name="close" size={12} /></button
					>
				</span>
			{/if}
		</div>

		<!-- Dimmed rather than blanked while switching people, so the layout holds still. -->
		<div
			class="overflow-hidden rounded-[14px] border border-line bg-card transition-opacity {entriesLoading
				? 'pointer-events-none opacity-40'
				: ''}"
		>
			<div class="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-2">
				<span class="font-mono text-[11px] text-ink-2">
					<strong class="text-ink">{entries.length}</strong>
					{entries.length === 1 ? 'entry' : 'entries'}{entries.length === ENTRY_LIMIT
						? ' · latest only'
						: ''}
				</span>
				<span class="font-mono text-[10px] text-ink-3">
					<span class="text-positive">+</span> they owe you ·
					<span class="text-negative">−</span> you owe them
				</span>
			</div>

			{#if entriesError}
				<p class="px-5 py-10 text-center font-mono text-[12px] text-negative">{entriesError}</p>
			{:else if groupedEntries.length === 0}
				<p class="px-5 py-10 text-center font-mono text-[12px] text-ink-3">
					{selectedPerson ? `Nothing with ${selectedPerson.nickname} yet` : 'No entries yet'}
				</p>
			{:else}
				{#each groupedEntries as group, gi (group.key)}
					<div
						class="{gi > 0
							? 'border-t border-line'
							: ''} bg-cream-2 px-5 py-3 font-mono text-[10px] font-medium tracking-widest text-ink-2 uppercase"
					>
						{group.label}
					</div>
					<div class="divide-y divide-line">
						{#each group.rows as entry (entry.id)}
							{@const nickname = peopleById.get(entry.person_id)?.nickname ?? 'Unknown'}
							{@const theyOwe = entry.amount >= 0}
							<div
								class="grid grid-cols-[28px_1fr_auto_auto_40px] items-center gap-2 px-5 py-3 transition-colors hover:bg-cream-2"
							>
								<div
									class="flex items-center justify-center {theyOwe
										? 'text-positive'
										: 'text-negative'}"
								>
									<Icon name={theyOwe ? 'income' : 'expense'} size={16} strokeWidth={2.5} />
								</div>
								<div class="flex min-w-0 items-center gap-2">
									<span class="truncate text-[14px] font-medium text-ink">{entry.title}</span>
									{#if entry.transaction_id}
										<span
											class="inline-flex shrink-0 items-center gap-1 rounded-full bg-cream-2 px-[8px] py-[2px] font-mono text-[10px] text-ink-2"
											title="Split from a shared expense — your share is in Transactions"
										>
											<Icon name="link" size={10} />
											shared
										</span>
									{/if}
								</div>
								<!-- Always rendered so the grid columns line up; empty when filtered to one person. -->
								<span>
									{#if !selectedPerson}
										<span
											class="inline-block rounded-full border border-accent/25 bg-accent-soft px-[8px] py-[2px] font-mono text-[10px] font-medium text-accent"
										>
											{nickname}
										</span>
									{/if}
								</span>
								<span
									class="text-right font-mono text-[13px] font-medium {theyOwe
										? 'text-positive'
										: 'text-negative'}"
									title={theyOwe ? `${nickname} owes you` : `You owe ${nickname}`}
								>
									{signed(entry.amount)}
								</span>
								<div class="flex justify-end">
									<IconButton
										icon="trash"
										label="Delete entry"
										tone="negative"
										onclick={() => openDeleteConfirm(entry)}
									/>
								</div>
							</div>
						{/each}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<LedgerEntryFormModal
	bind:open={entryModalOpen}
	people={balances}
	person={modalPerson}
	settle={settleMode}
	onsaved={refresh}
/>

<SharedExpenseModal
	bind:open={splitModalOpen}
	people={balances}
	{expenseCategories}
	onsaved={refresh}
/>

<ConfirmModal
	bind:open={confirmOpen}
	title="Delete entry"
	message={deletingEntry
		? `Delete "${deletingEntry.title}"?${deletingEntry.transaction_id ? ' Your share of the shared expense stays in Transactions.' : ''} This can't be undone.`
		: ''}
	confirmLabel="Delete"
	onconfirm={async () => {
		if (!deletingEntry) return;
		await deleteLedgerEntry(deletingEntry.id);
		await refresh();
	}}
/>
