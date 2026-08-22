<script lang="ts">
	import type { Snippet } from 'svelte';
	import IconButton from './IconButton.svelte';

	let {
		open = $bindable(false),
		title,
		width = 'max-w-[400px]',
		children
	}: {
		open?: boolean;
		title: string;
		/** Tailwind max-width class; widen for forms that don't fit the default. */
		width?: string;
		children: Snippet;
	} = $props();

	function close() {
		open = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) close();
	}
</script>

<svelte:window onkeydown={open ? handleKeydown : undefined} />

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 p-4 backdrop-blur-[2px]"
		onclick={handleBackdropClick}
		role="presentation"
	>
		<div
			class="flex max-h-[88vh] w-full flex-col rounded-[14px] border border-line bg-card p-7 shadow-[0_2px_8px_rgba(44,31,14,.08),0_8px_32px_rgba(44,31,14,.06)] {width}"
			role="dialog"
			aria-modal="true"
			aria-label={title}
		>
			<div class="mb-[22px] flex shrink-0 items-center justify-between">
				<h2 class="font-serif text-[17px] font-semibold text-ink">{title}</h2>
				<IconButton icon="close" label="Close" onclick={close} size={18} />
			</div>
			<!-- `-mx-1 px-1` keeps focus rings from being clipped by the scroll container. -->
			<div class="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
				{@render children()}
			</div>
		</div>
	</div>
{/if}
