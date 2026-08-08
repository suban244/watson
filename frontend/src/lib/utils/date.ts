/** Local (not UTC) YYYY-MM-DD key for a timestamp, so grouping matches the user's calendar day. */
export function toLocalDateKey(date: Date | string): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	const month = `${d.getMonth() + 1}`.padStart(2, '0');
	const day = `${d.getDate()}`.padStart(2, '0');
	return `${d.getFullYear()}-${month}-${day}`;
}

export function formatDateLabel(isoDate: string): string {
	const now = new Date();
	const todayKey = toLocalDateKey(now);
	const yesterday = new Date(now);
	yesterday.setDate(now.getDate() - 1);
	const yesterdayKey = toLocalDateKey(yesterday);

	// parse as local midnight so the weekday isn't shifted by the UTC offset
	const d = new Date(`${isoDate}T00:00:00`);
	const weekdayMonthDay = d.toLocaleDateString('en-US', {
		weekday: 'short',
		month: 'short',
		day: 'numeric'
	});

	if (isoDate === todayKey) return `Today · ${weekdayMonthDay}`;
	if (isoDate === yesterdayKey) return `Yesterday · ${weekdayMonthDay}`;

	if (d.getFullYear() === now.getFullYear()) {
		return weekdayMonthDay;
	}
	return d.toLocaleDateString('en-US', {
		weekday: 'short',
		month: 'short',
		day: 'numeric',
		year: 'numeric'
	});
}
