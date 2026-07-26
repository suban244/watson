import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	// SPA mode: build to static files served by Caddy (no Node server). See
	// src/routes/+layout.ts for the matching `ssr = false`. To restore SSR,
	// swap back to @sveltejs/adapter-node and follow the note in +layout.ts.
	kit: { adapter: adapter({ fallback: 'index.html' }) }
};

export default config;
