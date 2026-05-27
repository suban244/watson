export function formatDateLabel(isoDate: string): string {
	const now = new Date();
	const todayKey = now.toISOString().split('T')[0];
	const yesterday = new Date(now);
	yesterday.setDate(now.getDate() - 1);
	const yesterdayKey = yesterday.toISOString().split('T')[0];

	const d = new Date(isoDate);
	const monthDay = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

	if (isoDate === todayKey) return `Today · ${monthDay}`;
	if (isoDate === yesterdayKey) return `Yesterday · ${monthDay}`;

	if (d.getFullYear() === now.getFullYear()) {
		return monthDay;
	}
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
