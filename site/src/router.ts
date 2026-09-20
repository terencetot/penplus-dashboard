/**
 * A minimal hash router. Five screens, one question each (CLAUDE.md): the
 * route is the whole of the app's navigable state, so a link to
 * #/indicators/2.5 or #/countries/GHA is always shareable and printable.
 */
export type Route =
  | { screen: "overview" }
  | { screen: "indicator"; code: string }
  | { screen: "country"; iso3: string }
  | { screen: "quality" }
  | { screen: "facilities" };

const DEFAULT_INDICATOR = "2.5";
const DEFAULT_COUNTRY = "GHA";

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  switch (parts[0]) {
    case "indicators":
      return { screen: "indicator", code: parts[1] ?? DEFAULT_INDICATOR };
    case "countries":
      return { screen: "country", iso3: (parts[1] ?? DEFAULT_COUNTRY).toUpperCase() };
    case "quality":
      return { screen: "quality" };
    case "facilities":
      return { screen: "facilities" };
    case "overview":
    default:
      return { screen: "overview" };
  }
}

export function routeToHash(route: Route): string {
  switch (route.screen) {
    case "indicator":
      return `#/indicators/${route.code}`;
    case "country":
      return `#/countries/${route.iso3}`;
    case "quality":
      return "#/quality";
    case "facilities":
      return "#/facilities";
    default:
      return "#/overview";
  }
}

export function navigate(route: Route): void {
  location.hash = routeToHash(route);
}

export function onRouteChange(fn: (route: Route) => void): () => void {
  const handler = () => fn(parseRoute(location.hash));
  window.addEventListener("hashchange", handler);
  return () => window.removeEventListener("hashchange", handler);
}

export function currentRoute(): Route {
  return parseRoute(location.hash);
}
