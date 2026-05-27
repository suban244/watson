<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children } = $props();

	function isActive(href: string) {
		return page.url.pathname === href;
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="flex h-screen overflow-hidden">
	<!-- ── Sidebar ── -->
	<nav class="flex flex-col w-[220px] min-w-[220px] bg-white border-r border-orange-200 overflow-hidden">

		<!-- Brand -->
		<div class="px-5 pt-6 pb-5 border-b border-orange-200">
			<div class="w-[34px] h-[34px] bg-orange-600 rounded-[10px] flex items-center justify-center text-white font-serif text-base font-semibold mb-[10px]">
				W
			</div>
			<div class="font-serif text-[15px] font-semibold text-stone-900 tracking-[0.01em]">Watson Finance</div>
			<div class="font-mono text-[11px] text-stone-400 mt-px">personal</div>
		</div>

		<!-- Nav items -->
		<div class="flex-1 overflow-y-auto py-2">
			<p class="px-[14px] pt-4 pb-1 text-[10px] font-semibold text-stone-400 uppercase tracking-widest font-mono">Overview</p>

			<a href="/"
				class="flex items-center gap-[10px] px-[14px] py-[9px] mx-2 rounded-lg text-sm font-medium no-underline transition-colors
					{isActive('/') ? 'bg-orange-100 text-orange-700 font-semibold' : 'text-stone-600 hover:bg-orange-50 hover:text-stone-900'}">
				<div class="w-7 h-7 rounded-[7px] flex items-center justify-center text-[13px] shrink-0 transition-colors
					{isActive('/') ? 'bg-orange-600 text-white' : 'bg-stone-100'}">⊞</div>
				Dashboard
			</a>

			<p class="px-[14px] pt-4 pb-1 text-[10px] font-semibold text-stone-400 uppercase tracking-widest font-mono">Money</p>

			<a href="/transactions"
				class="flex items-center gap-[10px] px-[14px] py-[9px] mx-2 rounded-lg text-sm font-medium no-underline transition-colors
					{isActive('/transactions') ? 'bg-orange-100 text-orange-700 font-semibold' : 'text-stone-600 hover:bg-orange-50 hover:text-stone-900'}">
				<div class="w-7 h-7 rounded-[7px] flex items-center justify-center text-[13px] shrink-0 transition-colors
					{isActive('/transactions') ? 'bg-orange-600 text-white' : 'bg-stone-100'}">⇅</div>
				Transactions
			</a>

			<a href="/budget"
				class="flex items-center gap-[10px] px-[14px] py-[9px] mx-2 rounded-lg text-sm font-medium no-underline transition-colors
					{isActive('/budget') ? 'bg-orange-100 text-orange-700 font-semibold' : 'text-stone-600 hover:bg-orange-50 hover:text-stone-900'}">
				<div class="w-7 h-7 rounded-[7px] flex items-center justify-center text-[13px] shrink-0 transition-colors
					{isActive('/budget') ? 'bg-orange-600 text-white' : 'bg-stone-100'}">◧</div>
				Budget
			</a>

			<p class="px-[14px] pt-4 pb-1 text-[10px] font-semibold text-stone-400 uppercase tracking-widest font-mono">Insights</p>

			<a href="/analytics"
				class="flex items-center gap-[10px] px-[14px] py-[9px] mx-2 rounded-lg text-sm font-medium no-underline transition-colors
					{isActive('/analytics') ? 'bg-orange-100 text-orange-700 font-semibold' : 'text-stone-600 hover:bg-orange-50 hover:text-stone-900'}">
				<div class="w-7 h-7 rounded-[7px] flex items-center justify-center text-[13px] shrink-0 transition-colors
					{isActive('/analytics') ? 'bg-orange-600 text-white' : 'bg-stone-100'}">◟</div>
				Analytics
			</a>
		</div>

		<!-- Footer -->
		<div class="px-5 py-4 border-t border-orange-200 flex items-center gap-[10px]">
			<div class="w-[34px] h-[34px] rounded-full bg-orange-100 border-2 border-orange-600 flex items-center justify-center text-[12px] font-semibold text-orange-600 shrink-0">W</div>
			<div>
				<div class="text-[13px] font-semibold text-stone-900">Watson</div>
				<div class="font-mono text-[11px] text-stone-400">personal</div>
			</div>
		</div>
	</nav>

	<!-- ── Main content ── -->
	<main class="flex-1 overflow-y-auto overflow-x-hidden bg-orange-50 w-full">
		{@render children()}
	</main>
</div>
