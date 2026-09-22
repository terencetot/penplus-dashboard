import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";

import { getManifest } from "@/lib/bundle";
import { getLang, LANG_LABELS, LANGS, onLangChange, setLang, t, type Lang } from "@/lib/i18n";
import { currentRoute, navigate, onRouteChange, type Route } from "@/router";
import { isDemoMode, setDemoMode } from "@/lib/demo";
import { renderOverview } from "@/screens/overview";
import { renderIndicatorDetail } from "@/screens/indicator-detail";
import { renderCountryProfile } from "@/screens/country-profile";
import { renderDataQuality } from "@/screens/data-quality";
import { renderFacilities } from "@/screens/facilities";
import { renderImplementation } from "@/screens/implementation";
import { icon } from "@/components/icons";

const THEME_KEY = "penplus.theme";
type Theme = "system" | "light" | "dark";

function applyTheme(theme: Theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}

function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    /* per-viewer convenience only */
  }
  return "system";
}

const NAV: { route: Route; num: number; key: string }[] = [
  { route: { screen: "overview" }, num: 1, key: "nav.overview" },
  { route: { screen: "indicator", code: "2.5" }, num: 2, key: "nav.indicator" },
  { route: { screen: "country", iso3: "GHA" }, num: 3, key: "nav.country" },
  { route: { screen: "implementation" }, num: 4, key: "nav.implementation" },
  { route: { screen: "quality" }, num: 5, key: "nav.quality" },
  { route: { screen: "facilities" }, num: 6, key: "nav.facilities" },
];

function screenOf(route: Route): Route["screen"] {
  return route.screen;
}

async function renderApp() {
  const app = document.getElementById("app")!;
  const manifest = await getManifest();

  app.innerHTML = `
    <header class="app-header">
      <div class="app-header__bar">
        <div class="app-header__logos">
          <a href="https://www.afro.who.int/" target="_blank" rel="noopener">
            <img src="${import.meta.env.BASE_URL}assets/logos/who-afro.png" alt="WHO African Region" />
          </a>
          <div class="app-header__divider"></div>
          <a href="https://helmsleytrust.org/" target="_blank" rel="noopener">
            <img
              class="app-header__logo--helmsley"
              src="${import.meta.env.BASE_URL}assets/logos/helmsley-charitable-trust.svg"
              alt="The Leona M. and Harry B. Helmsley Charitable Trust"
            />
          </a>
          <div class="app-header__divider"></div>
          <div>
            <p class="app-header__title">${t("app.title")}</p>
            <p class="app-header__subtitle">${t("app.subtitle")}</p>
          </div>
        </div>
        <div class="app-header__spacer"></div>
        <div class="app-header__controls">
          <select class="lang-switch no-print" id="lang-switch" aria-label="${t("footer.language")}">
            ${LANGS.map((l) => `<option value="${l}" ${l === getLang() ? "selected" : ""}>${LANG_LABELS[l]}</option>`).join("")}
          </select>
          <select class="theme-switch no-print" id="theme-switch" aria-label="${t("footer.theme")}">
            <option value="system">Auto</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
          <button type="button" class="btn no-print" id="print-btn">${t("common.print")}</button>
          <button type="button" class="btn no-print" id="demo-toggle-btn">${isDemoMode() ? t("demo.exit") : t("demo.enter")}</button>
        </div>
      </div>
      <nav class="app-nav" aria-label="Screens">
        <ul class="app-nav__list">
          ${NAV.map((n) => `<li><a class="app-nav__link" href="#" data-screen="${n.route.screen}"><span class="num-badge">${n.num}</span>${t(n.key)}</a></li>`).join("")}
        </ul>
      </nav>
    </header>
    ${isDemoMode() ? `<div class="demo-banner no-print" role="status">${t("demo.banner")}</div>` : ""}
    <main class="app-main" id="main-content" tabindex="-1"></main>
    <footer class="app-footer">
      <div class="app-footer__bar app-footer__brand">
        <div class="app-footer__brand-logos">
          <img src="${import.meta.env.BASE_URL}assets/logos/who-afro.png" alt="WHO African Region" />
          <div class="app-header__divider"></div>
          <img
            class="app-header__logo--helmsley"
            src="${import.meta.env.BASE_URL}assets/logos/helmsley-charitable-trust.svg"
            alt="The Leona M. and Harry B. Helmsley Charitable Trust"
            loading="lazy"
          />
          <div class="app-header__divider"></div>
          <span class="app-footer__copyright">${t("footer.copyright", { year: new Date(manifest.built_at).getFullYear() })}</span>
        </div>
        <button type="button" class="back-to-top no-print" id="back-to-top-btn" aria-label="${t("footer.back_to_top")}">
          ${icon("arrowUp")}
        </button>
      </div>
    </footer>
  `;

  const main = document.getElementById("main-content")!;

  const navLinks = Array.from(app.querySelectorAll<HTMLAnchorElement>(".app-nav__link"));
  for (const link of navLinks) {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const entry = NAV.find((n) => n.route.screen === link.dataset.screen);
      if (entry) navigate(entry.route);
    });
  }

  function highlightNav(route: Route) {
    for (const link of navLinks) {
      const active = link.dataset.screen === screenOf(route);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
  }

  async function dispatch(route: Route) {
    highlightNav(route);
    switch (route.screen) {
      case "overview":
        return renderOverview(main);
      case "indicator":
        return renderIndicatorDetail(main, route.code);
      case "country":
        return renderCountryProfile(main, route.iso3);
      case "implementation":
        return renderImplementation(main);
      case "quality":
        return renderDataQuality(main);
      case "facilities":
        return renderFacilities(main);
    }
  }

  onRouteChange((route) => {
    dispatch(route).catch((err) => {
      console.error(err);
      main.innerHTML = `<p class="callout callout--empty">${t("empty.bundle_error")}</p>`;
    });
  });
  dispatch(currentRoute()).catch((err) => {
    console.error(err);
    main.innerHTML = `<p class="callout callout--empty">${t("empty.bundle_error")}</p>`;
  });

  document.getElementById("lang-switch")!.addEventListener("change", (e) => {
    setLang((e.target as HTMLSelectElement).value as Lang);
  });
  document.getElementById("theme-switch")!.addEventListener("change", (e) => {
    const theme = (e.target as HTMLSelectElement).value as Theme;
    applyTheme(theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* per-viewer convenience only */
    }
  });
  (document.getElementById("theme-switch") as HTMLSelectElement).value = initialTheme();
  document.getElementById("print-btn")!.addEventListener("click", () => window.print());
  document.getElementById("demo-toggle-btn")!.addEventListener("click", () => {
    setDemoMode(!isDemoMode());
    navigate({ screen: "overview" });
    renderApp();
  });
  document.getElementById("back-to-top-btn")!.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

applyTheme(initialTheme());
onLangChange(() => renderApp());
renderApp().catch((err) => {
  console.error(err);
  document.getElementById("app")!.innerHTML =
    `<p class="callout callout--empty" style="margin:2rem">${t("empty.bundle_error")}</p>`;
});
