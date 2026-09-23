import { t } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";
import { navigate } from "@/router";
import { statusFromImplementationStep, statusKey } from "@/lib/status";
import type { ImplementationCountry, ImplementationStepDim } from "@/lib/types";

const STATUS_MARK: Record<string, string> = {
  met: "✓",
  partly_met: "~",
  not_met: "✗",
  not_reported: "·",
};

function highestPhaseLabel(n: number): string {
  return n === 0 ? t("screen_impl.not_started") : t("screen_impl.phase_n", { n });
}

/** Same three-state read as the phase-grid marks: grey until started,
 * amber while any phase is still open, green once every phase is met. */
function highestPhaseChipClass(n: number, maxPhase: number): string {
  if (n === 0) return "chip--not_reported";
  if (n >= maxPhase) return "chip--met";
  return "chip--partly_met";
}

/**
 * The countries x steps detail grid, purpose-built rather than assembled
 * from the generic Column[]/buildTable helper: a two-row grouped header
 * (phase, then step number) and a frozen country column are structural
 * requirements a flat column list can't express, and both are what a
 * 16-column, 31-row table actually needs to stay legible -- a reader must
 * always be able to tell which phase a step belongs to and which country a
 * row is, even mid-scroll. See docs/architecture.md, "Implementation phases".
 */
export function buildPhaseGrid(
  caption: string,
  steps: ImplementationStepDim[],
  countries: ImplementationCountry[],
  pageSize = 20,
): HTMLElement {
  const phaseNos = [...new Set(steps.map((s) => s.phase_no))].sort((a, b) => a - b);
  const stepsByPhase = new Map(phaseNos.map((p) => [p, steps.filter((s) => s.phase_no === p)]));
  const maxPhase = Math.max(...phaseNos);

  const host = document.createElement("div");
  let page = 0;
  const totalPages = Math.max(1, Math.ceil(countries.length / pageSize));

  function render() {
    const start = page * pageSize;
    const pageRows = countries.slice(start, start + pageSize);

    const wrap = document.createElement("div");
    wrap.className = "data-table-wrap phase-grid-wrap";

    const table = document.createElement("table");
    table.className = "data-table phase-grid";

    const cap = document.createElement("caption");
    cap.textContent = caption;
    table.appendChild(cap);

    const thead = document.createElement("thead");

    // ---- header row 1: phase groups, each spanning its own steps
    const phaseRow = document.createElement("tr");
    phaseRow.className = "phase-grid__phase-row";
    const pinCountry = document.createElement("th");
    pinCountry.rowSpan = 2;
    pinCountry.scope = "col";
    pinCountry.className = "phase-grid__pin";
    pinCountry.textContent = t("common.select_country");
    phaseRow.appendChild(pinCountry);

    const highestTh = document.createElement("th");
    highestTh.rowSpan = 2;
    highestTh.scope = "col";
    highestTh.textContent = t("screen_impl.column.highest_phase");
    phaseRow.appendChild(highestTh);

    phaseNos.forEach((phaseNo, i) => {
      const stepsOfPhase = stepsByPhase.get(phaseNo)!;
      const th = document.createElement("th");
      th.colSpan = stepsOfPhase.length;
      th.scope = "colgroup";
      th.className = `phase-grid__phase-band phase-grid__phase-band--${i % 2 === 0 ? "a" : "b"} phase-grid__band-end`;
      th.textContent = t("screen_impl.phase_n", { n: phaseNo });
      th.title = stepsOfPhase[0]!.phase_label;
      phaseRow.appendChild(th);
    });
    thead.appendChild(phaseRow);

    // ---- header row 2: step numbers, one cell per step, banded to match its phase
    const stepRow = document.createElement("tr");
    stepRow.className = "phase-grid__step-row";
    phaseNos.forEach((phaseNo, i) => {
      const stepsOfPhase = stepsByPhase.get(phaseNo)!;
      stepsOfPhase.forEach((s, j) => {
        const th = document.createElement("th");
        th.scope = "col";
        th.className = `phase-grid__phase-band phase-grid__phase-band--${i % 2 === 0 ? "a" : "b"}${j === stepsOfPhase.length - 1 ? " phase-grid__band-end" : ""}`;
        th.textContent = String(s.step_no);
        th.title = `${s.phase_label}: ${s.step_no}. ${s.step_label}`;
        stepRow.appendChild(th);
      });
    });
    thead.appendChild(stepRow);
    table.appendChild(thead);

    // ---- body
    const tbody = document.createElement("tbody");
    for (const c of pageRows) {
      const tr = document.createElement("tr");
      tr.addEventListener("click", () => navigate({ screen: "country", iso3: c.iso3 }));
      tr.style.cursor = "pointer";

      const nameTd = document.createElement("td");
      nameTd.className = "phase-grid__pin";
      nameTd.textContent = c.name;
      tr.appendChild(nameTd);

      const highestTd = document.createElement("td");
      const chipClass = highestPhaseChipClass(c.highest_phase_completed, maxPhase);
      highestTd.innerHTML = `<span class="chip ${chipClass}">${highestPhaseLabel(c.highest_phase_completed)}</span>`;
      tr.appendChild(highestTd);

      phaseNos.forEach((phaseNo) => {
        const stepsOfPhase = stepsByPhase.get(phaseNo)!;
        stepsOfPhase.forEach((s, j) => {
          const row = c.steps.find((r) => r.step_no === s.step_no);
          const status = statusFromImplementationStep(row?.status ?? null);
          const title = [
            `${s.phase_label}: ${s.step_no}. ${s.step_label}`,
            t(statusKey(status)),
            row?.as_of ? `${t("common.as_of")} ${fmtDate(row.as_of)}` : "",
            row?.source ?? "",
          ]
            .filter(Boolean)
            .join(" · ");
          const td = document.createElement("td");
          td.className = `phase-grid__cell${j === stepsOfPhase.length - 1 ? " phase-grid__band-end" : ""}`;
          const escapedTitle = title.replace(/"/g, "&quot;");
          td.innerHTML = `<span class="phase-grid__mark phase-grid__mark--${status}" title="${escapedTitle}" aria-label="${escapedTitle}">${STATUS_MARK[status] ?? "?"}</span>`;
          tr.appendChild(td);
        });
      });
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    wrap.appendChild(table);

    const pager = document.createElement("div");
    pager.className = "pager";
    const prev = document.createElement("button");
    prev.type = "button";
    prev.className = "btn";
    prev.textContent = t("common.previous");
    prev.disabled = page === 0;
    prev.addEventListener("click", () => {
      page -= 1;
      render();
    });
    const label = document.createElement("span");
    label.className = "pager__label";
    label.textContent = t("common.page_of", { page: page + 1, total: totalPages, n: countries.length });
    const next = document.createElement("button");
    next.type = "button";
    next.className = "btn";
    next.textContent = t("common.next");
    next.disabled = page >= totalPages - 1;
    next.addEventListener("click", () => {
      page += 1;
      render();
    });
    pager.append(prev, label, next);

    host.replaceChildren(wrap, pager);
  }
  render();
  return host;
}
