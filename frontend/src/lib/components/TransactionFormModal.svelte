<script lang="ts">
	import Modal from './Modal.svelte';
	import Icon from './Icon.svelte';
	import { createTransaction, updateTransaction, MAX_TAGS_PER_TRANSACTION } from '$lib/api';
	import type { Tag, Transaction } from '$lib/api';

	let {
		open = $bindable(false),
		transaction = null,
		expenseCategories,
		incomeCategories,
		tags = [],
		onsaved
	}: {
		open?: boolean;
		transaction?: Transaction | null;
		expenseCategories: string[];
		incomeCategories: string[];
		/** Active tags only; archived ones already on the transaction are added below. */
		tags?: Tag[];
		onsaved: (tx: Transaction) => void;
	} = $props();

	let title = $state('');
	let amount = $state('');
	let date = $state('');
	let isExpense = $state(true);
	let category = $state('');
	let description = $state('');
	let selectedTags = $state<string[]>([]);
	let tagPickerOpen = $state(false);
	let tagSearch = $state('');
	let tagFieldEl = $state<HTMLDivElement | null>(null);
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

	// Archived tags stay legal on a transaction that already carries them (the backend
	// grandfathers them), so show those alongside the active list rather than dropping
	// them silently on the next save.
	let tagOptions = $derived.by(() => {
		const known = new Set(tags.map((t) => t.slug));
		const orphans = selectedTags
			.filter((slug) => !known.has(slug))
			.map((slug) => ({ slug, name: slug, archived: true }));
		return [...tags.map((t) => ({ slug: t.slug, name: t.name, archived: false })), ...orphans];
	});

	let tagLimitReached = $derived(selectedTags.length >= MAX_TAGS_PER_TRANSACTION);
	let tagLabels = $derived(new Map(tagOptions.map((o) => [o.slug, o.name])));

	let filteredTagOptions = $derived.by(() => {
		const q = tagSearch.trim().toLowerCase();
		if (!q) return tagOptions;
		return tagOptions.filter(
			(o) => o.name.toLowerCase().includes(q) || o.slug.includes(q)
		);
	});

	function toggleTag(slug: string) {
		if (selectedTags.includes(slug)) {
			selectedTags = selectedTags.filter((s) => s !== slug);
		} else if (!tagLimitReached) {
			selectedTags = [...selectedTags, slug];
		}
	}

	// Close the picker on an outside click. Capture phase so it still fires when the
	// click lands on something that stops propagation.
	$effect(() => {
		if (!tagPickerOpen) return;
		const onDocClick = (e: MouseEvent) => {
			if (tagFieldEl && !tagFieldEl.contains(e.target as Node)) tagPickerOpen = false;
		};
		document.addEventListener('click', onDocClick, true);
		return () => document.removeEventListener('click', onDocClick, true);
	});

	/** Escape closes the picker rather than the whole modal — Modal listens on
	 * `window`, so stopping propagation here keeps the transaction form open. */
	function handleTagKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && tagPickerOpen) {
			e.stopPropagation();
			tagPickerOpen = false;
		}
	}

	$effect(() => {
		if (!open) return;
		title = transaction?.title ?? '';
		amount = transaction ? String(transaction.amount) : '';
		date = transaction ? transaction.date.slice(0, 10) : new Date().toISOString().slice(0, 10);
		isExpense = transaction?.is_expense ?? true;
		category = transaction?.category ?? '';
		description = transaction?.description ?? '';
		selectedTags = [...(transaction?.tags ?? [])];
		tagPickerOpen = false;
		tagSearch = '';
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
				description: description.trim() || null,
				// An empty array clears the tags; the PATCH endpoint only skips `null`.
				tags: selectedTags
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

		{#if tagOptions.length > 0}
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<div bind:this={tagFieldEl} class="relative" onkeydown={handleTagKeydown} role="none">
				<div class="mb-[5px] flex items-baseline justify-between">
					<span class="font-mono text-[9px] tracking-widest text-ink-3 uppercase">Tags</span>
					<span class="font-mono text-[9px] text-ink-3">
						{selectedTags.length}/{MAX_TAGS_PER_TRANSACTION}
					</span>
				</div>

				<button
					type="button"
					onclick={() => (tagPickerOpen = !tagPickerOpen)}
					aria-haspopup="listbox"
					aria-expanded={tagPickerOpen}
					class="flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border bg-cream px-[14px] py-[9px] text-left transition-colors
						{tagPickerOpen ? 'border-accent' : 'border-line hover:border-accent'}"
				>
					{#if selectedTags.length === 0}
						<span class="text-[14px] text-ink-3">Select tags…</span>
					{:else}
						<span class="flex flex-wrap gap-1">
							{#each selectedTags as slug (slug)}
								<span
									class="rounded-full bg-accent-soft px-[8px] py-[2px] font-mono text-[10px] font-medium text-accent"
								>
									{tagLabels.get(slug) ?? slug}
								</span>
							{/each}
						</span>
					{/if}
					<Icon
						name="chevronDown"
						size={14}
						class="text-ink-2 transition-transform {tagPickerOpen ? 'rotate-180' : ''}"
					/>
				</button>

				{#if tagPickerOpen}
					<div
						class="absolute top-full right-0 left-0 z-10 mt-1 overflow-hidden rounded-lg border border-line bg-card shadow-[0_4px_16px_rgba(44,31,14,.12)]"
					>
						<!-- Search only earns its space once the list is long enough to scroll. -->
						{#if tagOptions.length > 6}
							<div class="flex items-center gap-2 border-b border-line px-[14px] py-2">
								<Icon name="search" size={14} class="text-ink-3" />
								<!-- svelte-ignore a11y_autofocus -->
								<input
									type="text"
									autofocus
									placeholder="Filter tags…"
									bind:value={tagSearch}
									class="flex-1 bg-transparent font-mono text-[12px] text-ink-2 placeholder-ink-3 outline-none"
								/>
							</div>
						{/if}

						<div class="max-h-[184px] overflow-y-auto" role="listbox" aria-multiselectable="true">
							{#each filteredTagOptions as opt (opt.slug)}
								{@const selected = selectedTags.includes(opt.slug)}
								<button
									type="button"
									role="option"
									aria-selected={selected}
									onclick={() => toggleTag(opt.slug)}
									disabled={!selected && tagLimitReached}
									title={!selected && tagLimitReached
										? `At most ${MAX_TAGS_PER_TRANSACTION} tags per transaction`
										: undefined}
									class="flex w-full cursor-pointer items-center gap-[10px] px-[14px] py-2 text-left transition-colors hover:bg-cream-2 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
								>
									<span
										class="flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors
											{selected ? 'border-accent bg-accent text-white' : 'border-line'}"
									>
										{#if selected}<Icon name="check" size={11} strokeWidth={3} />{/if}
									</span>
									<span class="truncate text-[13px] text-ink">{opt.name}</span>
									{#if opt.archived}
										<span class="ml-auto shrink-0 font-mono text-[10px] text-ink-3">archived</span>
									{/if}
								</button>
							{:else}
								<p class="px-[14px] py-3 text-center font-mono text-[11px] text-ink-3">
									No tags match “{tagSearch}”
								</p>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}

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
