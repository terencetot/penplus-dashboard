/**
 * Small hand-rolled inline SVG icons, stroke-only, single colour (currentColor).
 * No icon-font CDN: the specification's "no network calls at runtime" rule
 * covers more than the data bundle, and a handful of 24x24 paths costs less
 * than a webfont anyway.
 */
const base = (paths: string) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

export const icons = {
  facility: base(
    `<path d="M4 21V7l8-4 8 4v14"/><path d="M9 21v-6h6v6"/><path d="M9 11h.01M15 11h.01M9 15h.01M15 15h.01"/>`,
  ),
  patients: base(
    `<circle cx="9" cy="8" r="3"/><path d="M2 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2"/><circle cx="17" cy="8" r="2.4"/><path d="M17 13.2c2.3.4 4 2 4 4.3V21"/>`,
  ),
  pulse: base(`<path d="M3 12h4l2 8 4-16 2 8h6"/>`),
  training: base(
    `<path d="M22 9 12 4 2 9l10 5 10-5Z"/><path d="M6 11.5V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-4.5"/><path d="M22 9v6"/>`,
  ),
  target: base(
    `<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>`,
  ),
  map: base(`<path d="M9 4 3 6.5v13L9 17l6 3 6-2.5v-13L15 7 9 4Z"/><path d="M9 4v13M15 7v13"/>`),
  shield: base(
    `<path d="M12 3 4 6v6c0 4.4 3.2 7.6 8 9 4.8-1.4 8-4.6 8-9V6l-8-3Z"/><path d="m9 12 2 2 4-4"/>`,
  ),
  flag: base(`<path d="M5 21V4"/><path d="M5 5h11l-2 4 2 4H5"/>`),
  trend: base(`<path d="M4 17 10 10l4 3 6-8"/><path d="M14 5h6v6"/>`),
  grid: base(
    `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>`,
  ),
  alert: base(`<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4"/><path d="M12 17h.01"/>`),
  country: base(
    `<path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/>`,
  ),
  arrowUp: base(`<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>`),
};

export type IconName = keyof typeof icons;

export function icon(name: IconName): string {
  return icons[name];
}
