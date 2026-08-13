<script lang="ts">
	import Modal from './Modal.svelte';
	import { createTag, updateTag } from '$lib/api';
	import type { Tag } from '$lib/api';

	let {
		open = $bindable(false),
		tag = null,
		onsaved
	}: {
		open?: boolean;
		tag?: Tag | null;
		onsaved: (tag: Tag) => void;
	} = $props();

	let name = $state('');
	let description = $state('');
	let isPot = $state(false);
	let limitAmount = $state('');
	let excludeFromMonthly = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);

	/** Mirrors `slugify` in backend/app/services/tags.py, so the preview matches
	 * the slug the backend will actually store. */
	function slugify(value: string): string {
		return value
			.trim()
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-+|-+$/g, '')
			.slice(0, 50);
	}

	let slugPreview = $derived(slugify(name));

	$effect(() => {
		if (!open) return;
		name = tag?.name ?? '';
		description = tag?.description ?? '';
		isPot = tag?.is_pot ?? false;
		limitAmount = tag?.limit_amount != null ? String(tag.limit_amount) : '';
		excludeFromMonthly = tag?.exclude_from_monthly ?? false;
		error = null;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		if (!name.trim()) {
			error = 'Name is required';
			return;
		}
		if (!slugPreview) {
			error = 'Name must contain at least one letter or number';
			return;
		}

		let parsedLimit: number | null = null;
		if (isPot && limitAmount.trim()) {
			parsedLimit = parseFloat(limitAmount);
			if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
				error = 'Enter a valid limit, or leave it blank for an untracked pot';
				return;
			}
		}

		error = null;
		saving = true;
		try {
			// The backend rejects pot-only fields on a plain tag, so clear them when
			// `is_pot` is off rather than sending stale values.
			const payload = {
				name: name.trim(),
				description: description.trim() || null,
				is_pot: isPot,
				limit_amount: isPot ? parsedLimit : null,
				exclude_from_monthly: isPot ? excludeFromMonthly : false
			};
			// `slug` is omitted on edit — slugs are immutable once the tag exists.
			const result = tag ? await updateTag(tag.id, payload) : await createTag(payload);
			onsaved(result);
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save tag';
		} finally {
			saving = false;
		}
	}
</script>

<Modal bind:open title={tag ? 'Edit tag' : 'New tag'}>
	<form onsubmit={handleSubmit} class="flex flex-col gap-[14px]">
		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tag-name">
				Name
			</label>
			<input
				id="tag-name"
				type="text"
				bind:value={name}
				placeholder="e.g. Fifa Final 2026"
				class="w-full rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			/>
			{#if slugPreview}
				<p class="mt-[5px] font-mono text-[10px] text-ink-3">
					{tag ? 'slug' : 'will be saved as'}
					<span class="text-ink-2">{tag ? tag.slug : slugPreview}</span>
					{#if tag && tag.slug !== slugPreview}
						&nbsp;· slugs are immutable, so renaming won't change it
					{/if}
				</p>
			{/if}
		</div>

		<div>
			<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tag-description">
				Description
			</label>
			<textarea
				id="tag-description"
				bind:value={description}
				placeholder="When to apply this tag — the chat agent reads this…"
				rows="2"
				class="w-full resize-none rounded-lg border border-line bg-cream px-[14px] py-[9px] text-[14px] text-ink outline-none focus:border-accent"
			></textarea>
		</div>

		<div>
			<span class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase">Type</span>
			<div class="flex overflow-hidden rounded-lg border border-line">
				<button
					type="button"
					onclick={() => (isPot = false)}
					class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
						{!isPot ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
				>
					Tag
				</button>
				<button
					type="button"
					onclick={() => (isPot = true)}
					class="flex-1 cursor-pointer border-none py-[9px] text-[13px] font-medium transition-colors
						{isPot ? 'bg-accent text-white' : 'bg-transparent text-ink-2 hover:bg-cream-2'}"
				>
					Pot
				</button>
			</div>
			<p class="mt-[5px] font-mono text-[10px] text-ink-3">
				A pot is a tag that also tracks spend, optionally against a limit.
			</p>
		</div>

		{#if isPot}
			<div>
				<label class="mb-[5px] block font-mono text-[9px] tracking-widest text-ink-3 uppercase" for="tag-limit">
					Limit
				</label>
				<div class="flex items-center gap-2 rounded-lg border border-line bg-cream px-[14px] py-[6px]">
					<span class="font-mono text-[18px] font-medium text-ink-3">Rs.</span>
					<input
						id="tag-limit"
						type="number"
						min="0"
						step="0.01"
						bind:value={limitAmount}
						placeholder="no limit"
						class="w-full bg-transparent font-mono text-[18px] font-medium text-ink outline-none"
					/>
				</div>
				<p class="mt-[5px] font-mono text-[10px] text-ink-3">
					Leave blank to track spend without a cap.
				</p>
			</div>

			<label class="flex cursor-pointer items-center gap-[10px]">
				<input
					type="checkbox"
					bind:checked={excludeFromMonthly}
					class="rounded border-line text-accent focus:ring-accent"
				/>
				<span class="text-[13px] text-ink-2">Exclude from monthly totals</span>
			</label>
		{/if}

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
				{saving ? 'Saving…' : tag ? 'Save changes' : 'Create tag'}
			</button>
		</div>
	</form>
</Modal>
