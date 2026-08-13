<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';

	let { children } = $props();

	function isActive(href: string) {
		return page.url.pathname === href;
	}

	const sections: { heading: string; items: { href: string; label: string; icon: IconName }[] }[] = [
		{ heading: 'Overview', items: [{ href: '/', label: 'Dashboard', icon: 'dashboard' }] },
		{
			heading: 'Money',
			items: [
				{ href: '/transactions', label: 'Transactions', icon: 'transactions' },
				{ href: '/tags', label: 'Tags', icon: 'tag' },
				{ href: '/budget', label: 'Budget', icon: 'budget' }
			]
		},
		{ heading: 'Insights', items: [{ href: '/analytics', label: 'Analytics', icon: 'analytics' }] }
	];
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="flex h-screen overflow-hidden">
	<!-- ── Sidebar ── -->
	<nav class="flex flex-col w-[220px] min-w-[220px] bg-card border-r border-line overflow-hidden">

		<!-- Brand -->
		<div class="px-5 pt-6 pb-5 border-b border-line">
			<div class="w-[34px] h-[34px] bg-accent rounded-[10px] flex items-center justify-center text-white font-serif text-base font-semibold mb-[10px]">
				W
			</div>
			<div class="font-serif text-[15px] font-semibold text-ink tracking-[0.01em]">Watson Finance</div>
			<div class="font-mono text-[11px] text-ink-3 mt-px">personal</div>
		</div>

		<!-- Nav items -->
		<div class="flex-1 overflow-y-auto py-2">
			{#each sections as section (section.heading)}
				<p class="px-[14px] pt-4 pb-1 text-[10px] font-semibold text-ink-3 uppercase tracking-widest font-mono">
					{section.heading}
				</p>

				{#each section.items as item (item.href)}
					<a href={item.href}
						class="flex items-center gap-[10px] px-[14px] py-[9px] mx-2 rounded-lg text-sm font-medium no-underline transition-colors
							{isActive(item.href) ? 'bg-accent-soft text-accent font-semibold' : 'text-ink-2 hover:bg-cream-2 hover:text-ink'}">
						<div class="w-8 h-8 rounded-[8px] flex items-center justify-center shrink-0 transition-colors
							{isActive(item.href) ? 'bg-accent text-white' : 'bg-cream-2 text-ink-2'}">
							<Icon name={item.icon} size={18} />
						</div>
						{item.label}
					</a>
				{/each}
			{/each}
		</div>

		<!-- Footer -->
		<div class="px-5 py-4 border-t border-line flex items-center gap-[10px]">
			<div class="w-[34px] h-[34px] rounded-full bg-accent-soft border-2 border-accent flex items-center justify-center text-[12px] font-semibold text-accent shrink-0">W</div>
			<div>
				<div class="text-[13px] font-semibold text-ink">Watson</div>
				<div class="font-mono text-[11px] text-ink-3">personal</div>
			</div>
		</div>
	</nav>

	<!-- ── Main content ── -->
	<main class="flex-1 overflow-y-auto overflow-x-hidden bg-cream w-full">
		{@render children()}
	</main>
</div>
