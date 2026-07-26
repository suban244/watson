<script lang="ts">
	import Modal from './Modal.svelte';

	let {
		open = $bindable(false),
		title,
		message,
		confirmLabel = 'Confirm',
		onconfirm
	}: {
		open?: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		onconfirm: () => void | Promise<void>;
	} = $props();

	let busy = $state(false);
	let error = $state<string | null>(null);

	async function handleConfirm() {
		error = null;
		busy = true;
		try {
			await onconfirm();
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Something went wrong';
		} finally {
			busy = false;
		}
	}
</script>

<Modal bind:open {title}>
	<p class="text-[13px] text-ink-2">{message}</p>
	{#if error}
		<p class="mt-2 font-mono text-[11px] text-negative">{error}</p>
	{/if}
	<div class="mt-5 flex justify-end gap-[10px]">
		<button
			type="button"
			onclick={() => (open = false)}
			class="cursor-pointer rounded-lg border border-line bg-card px-[18px] py-[9px] text-[13px] font-semibold text-ink-2 transition-opacity hover:opacity-90"
		>
			Cancel
		</button>
		<button
			type="button"
			onclick={handleConfirm}
			disabled={busy}
			class="cursor-pointer rounded-lg bg-negative px-[18px] py-[9px] text-[13px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
		>
			{busy ? 'Deleting…' : confirmLabel}
		</button>
	</div>
</Modal>
