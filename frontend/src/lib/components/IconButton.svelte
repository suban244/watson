<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from './Icon.svelte';

	let {
		icon,
		label,
		tone = 'default',
		size = 16,
		disabled = false,
		onclick
	}: {
		icon: IconName;
		/** Shown as the hover tooltip and used as the accessible name — these
		 * buttons are icon-only, so this is the only thing that says what they do. */
		label: string;
		tone?: 'default' | 'accent' | 'warn' | 'positive' | 'negative';
		size?: number;
		disabled?: boolean;
		onclick?: (e: MouseEvent) => void;
	} = $props();

	const tones = {
		default: 'hover:bg-cream-2 hover:text-ink',
		accent: 'hover:bg-accent-soft hover:text-accent',
		warn: 'hover:bg-warn-soft hover:text-warn',
		positive: 'hover:bg-positive-soft hover:text-positive',
		negative: 'hover:bg-negative-soft hover:text-negative'
	};
</script>

<button
	type="button"
	{disabled}
	{onclick}
	title={label}
	aria-label={label}
	class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border-none bg-transparent text-ink-2 transition-colors disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent {tones[
		tone
	]}"
>
	<Icon name={icon} {size} />
</button>
