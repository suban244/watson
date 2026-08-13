<script lang="ts">
	import { onMount } from 'svelte';
	import { archiveTag, deleteTag, listTags, listTransactions, restoreTag } from '$lib/api';
	import type { Tag, TagStatus } from '$lib/api';
	import TagFormModal from '$lib/components/TagFormModal.svelte';
	import ConfirmModal from '$lib/components/ConfirmModal.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import IconButton from '$lib/components/IconButton.svelte';

	let tags = $state<Tag[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	/** slug → number of transactions carrying it. Drives the usage column and
	 * explains up front why a tag can't be hard-deleted. */
	let usage = $state(new Map<string, number>());

	let statusFilter = $state<TagStatus>('active');
	let kindFilter = $state<'all' | 'tags' | 'pots'>('all');

	let formOpen = $state(false);
	let editingTag = $state<Tag | null>(null);
	let confirmOpen = $state(false);
	let deletingTag = $state<Tag | null>(null);

	let visibleTags = $derived(
		tags
			.filter((t) => t.status === statusFilter)
			.filter((t) => kindFilter === 'all' || (kindFilter === 'pots' ? t.is_pot : !t.is_pot))
	);

	let activeCount = $derived(tags.filter((t) => t.status === 'active').length);
	let archivedCount = $derived(tags.filter((t) => t.status === 'archived').length);

	function upsertTag(tag: Tag) {
		const idx = tags.findIndex((t) => t.id === tag.id);
		if (idx === -1) tags = [...tags, tag];
		else {
			const next = [...tags];
			next[idx] = tag;
			tags = next;
		}
	}

	function openCreate() {
		editingTag = null;
		formOpen = true;
	}

	function openEdit(tag: Tag) {
		editingTag = tag;
		formOpen = true;
	}

	onMount(async () => {
		try {
			// Both statuses up front so the archived tab needs no second round trip.
			const [allTags, transactions] = await Promise.all([
				listTags(),
				listTransactions(1, 500)
			]);
			tags = allTags;
			const counts = new Map<string, number>();
			for (const tx of transactions) {
				for (const slug of tx.tags) counts.set(slug, (counts.get(slug) ?? 0) + 1);
			}
			usage = counts;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load tags';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-9 py-8">
	<!-- Page header -->
	<div class="mb-6 flex items-end justify-between">
		<div>
			<h1 class="font-serif text-[22px] font-semibold text-ink">Tags</h1>
			<p class="mt-[3px] font-mono text-[12px] text-ink-3">
				Labels for transactions · pots also track spend
			</p>
		</div>
		<button
			onclick={openCreate}
			class="flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-[18px] py-[9px] text-[13px] font-semibold text-white transition-all hover:-translate-y-px hover:opacity-90"
		>
			<Icon name="plus" />
			New tag
		</button>
	</div>

	{#if loading}
		<p class="font-mono text-[12px] text-ink-3">Loading tags…</p>
	{:else if error}
		<p class="font-mono text-[12px] text-negative">{error}</p>
	{:else}
		<!-- Filter bar -->
		<div class="flex flex-wrap items-center gap-[10px] rounded-t-[14px] border border-line bg-card p-4">
			{#each [
				{ key: 'active', label: `Active · ${activeCount}` },
				{ key: 'archived', label: `Archived · ${archivedCount}` }
			] as opt (opt.key)}
				<button
					onclick={() => (statusFilter = opt.key as TagStatus)}
					class="cursor-pointer rounded-lg border px-[14px] py-2 text-[12px] font-medium transition-colors
						{statusFilter === opt.key
						? 'border-accent bg-accent-soft text-accent'
						: 'border-line bg-card text-ink-2 hover:border-accent hover:text-accent'}"
				>
					{opt.label}
				</button>
			{/each}

			<span class="mx-1 h-5 w-px bg-line"></span>

			{#each [
				{ key: 'all', label: 'All' },
				{ key: 'tags', label: 'Tags' },
				{ key: 'pots', label: 'Pots' }
			] as opt (opt.key)}
				<button
					onclick={() => (kindFilter = opt.key as typeof kindFilter)}
					class="cursor-pointer rounded-lg border px-3 py-[6px] font-mono text-[11px] font-medium transition-colors
						{kindFilter === opt.key
						? 'border-accent bg-accent-soft text-accent'
						: 'border-line bg-card text-ink-2 hover:border-accent'}"
				>
					{opt.label}
				</button>
			{/each}
		</div>

		<!-- Tag list -->
		<div class="overflow-hidden rounded-b-[14px] border border-t-0 border-line bg-card shadow-sm">
			{#if visibleTags.length === 0}
				<p class="px-5 py-10 text-center font-mono text-[12px] text-ink-3">
					{statusFilter === 'active' ? 'No tags yet — create one to start labelling transactions.' : 'No archived tags.'}
				</p>
			{:else}
				<div class="divide-y divide-line">
					{#each visibleTags as tag (tag.id)}
						{@const count = usage.get(tag.slug) ?? 0}
						<div
							class="group grid grid-cols-[1fr_auto_auto_104px] items-center gap-3 px-5 py-3 transition-colors hover:bg-cream-2"
						>
							<div class="min-w-0">
								<div class="flex items-center gap-2">
									<span class="truncate text-[14px] font-medium text-ink">{tag.name}</span>
									{#if tag.is_pot}
										<span
											class="shrink-0 rounded-full bg-accent-soft px-[8px] py-[2px] font-mono text-[10px] font-medium text-accent"
										>
											pot
										</span>
									{/if}
									{#if tag.exclude_from_monthly}
										<span
											class="shrink-0 rounded-full bg-warn-soft px-[8px] py-[2px] font-mono text-[10px] font-medium text-warn"
										>
											off-budget
										</span>
									{/if}
								</div>
								<p class="mt-[2px] truncate font-mono text-[11px] text-ink-3">
									{tag.slug}{tag.description ? ` · ${tag.description}` : ''}
								</p>
							</div>

							<span class="font-mono text-[12px] text-ink-2">
								{#if tag.is_pot && tag.limit_amount != null}
									Rs. {tag.limit_amount.toFixed(2)}
								{:else if tag.is_pot}
									<span class="text-ink-3">no limit</span>
								{/if}
							</span>

							<span class="w-24 text-right font-mono text-[11px] text-ink-3">
								{count} {count === 1 ? 'tx' : 'txs'}
							</span>

							<!-- Always visible: these were `opacity-0` until row hover, which made
								 them impossible to discover. IconButton carries the hover feedback. -->
							<div class="flex items-center justify-end">
								<IconButton icon="edit" label="Edit tag" tone="accent" onclick={() => openEdit(tag)} />
								{#if tag.status === 'active'}
									<IconButton
										icon="archive"
										label="Archive — keeps it on existing transactions"
										tone="warn"
										onclick={async () => upsertTag(await archiveTag(tag.id))}
									/>
								{:else}
									<IconButton
										icon="restore"
										label="Restore — offer this tag again"
										tone="positive"
										onclick={async () => upsertTag(await restoreTag(tag.id))}
									/>
								{/if}
								<IconButton
									icon="trash"
									label={count > 0 ? `In use on ${count} transaction(s) — archive instead` : 'Delete tag'}
									tone="negative"
									disabled={count > 0}
									onclick={() => { deletingTag = tag; confirmOpen = true; }}
								/>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<TagFormModal bind:open={formOpen} tag={editingTag} onsaved={upsertTag} />

<ConfirmModal
	bind:open={confirmOpen}
	title="Delete tag"
	message={deletingTag
		? `Delete "${deletingTag.name}"? This can't be undone. Tags still on a transaction can only be archived.`
		: ''}
	confirmLabel="Delete"
	onconfirm={async () => {
		if (!deletingTag) return;
		await deleteTag(deletingTag.id);
		tags = tags.filter((t) => t.id !== deletingTag!.id);
	}}
/>
