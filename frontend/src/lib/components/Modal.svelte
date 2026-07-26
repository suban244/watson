<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title,
		children
	}: {
		open?: boolean;
		title: string;
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
			class="w-full max-w-[400px] rounded-[14px] border border-line bg-card p-7 shadow-[0_2px_8px_rgba(44,31,14,.08),0_8px_32px_rgba(44,31,14,.06)]"
			role="dialog"
			aria-modal="true"
			aria-label={title}
		>
			<div class="mb-[22px] flex items-center justify-between">
				<h2 class="font-serif text-[17px] font-semibold text-ink">{title}</h2>
				<button
					type="button"
					onclick={close}
					class="cursor-pointer border-none bg-transparent text-[20px] leading-none text-ink-3 transition-colors hover:text-ink"
					aria-label="Close"
				>
					✕
				</button>
			</div>
			{@render children()}
		</div>
	</div>
{/if}
