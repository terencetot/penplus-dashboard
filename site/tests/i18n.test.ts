import { beforeEach, describe, expect, it } from "vitest";
import { setLang, t } from "@/lib/i18n";

describe("i18n", () => {
  beforeEach(() => setLang("en"));

  it("translates a known key per language", () => {
    expect(t("nav.overview")).toBe("Regional overview");
    setLang("fr");
    expect(t("nav.overview")).toBe("Vue d'ensemble régionale");
    setLang("pt");
    expect(t("nav.overview")).toBe("Visão geral regional");
  });

  it("falls back to English for a language missing the key, then to the key itself", () => {
    expect(t("no.such.key")).toBe("no.such.key");
  });

  it("substitutes {placeholders}", () => {
    expect(t("screen1.hero.reporting", { n: 3, N: 31 })).toBe("3 of 31 countries reporting");
  });
});
