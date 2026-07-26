// SPA mode. The app has no server-side load functions or form actions, and all
// data is fetched client-side from /api/v1 (see src/lib/api.ts), so nothing is
// rendered on the server. This lets us ship static files served by Caddy with
// no Node process on the Pi (see svelte.config.js).
//
// TO RESTORE SSR: delete `ssr = false` below, switch svelte.config.js back to
// @sveltejs/adapter-node, and update the frontend service in prod.yml to run
// the Node server instead of serving static files via Caddy. Leaving this line
// in place while on adapter-node would silently disable SSR on every page.
export const ssr = false;

// Client-side routing for all pages; nothing needs prerendering.
export const prerender = false;
