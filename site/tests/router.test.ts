import { describe, expect, it } from "vitest";
import { parseRoute, routeToHash } from "@/router";

describe("router", () => {
  it("defaults to the overview screen", () => {
    expect(parseRoute("")).toEqual({ screen: "overview" });
    expect(parseRoute("#/")).toEqual({ screen: "overview" });
  });
  it("parses an indicator route with its code", () => {
    expect(parseRoute("#/indicators/2.6b")).toEqual({ screen: "indicator", code: "2.6b" });
  });
  it("parses a country route and upper-cases the ISO3", () => {
    expect(parseRoute("#/countries/gha")).toEqual({ screen: "country", iso3: "GHA" });
  });
  it("round-trips route -> hash -> route", () => {
    const route = { screen: "country" as const, iso3: "ZMB" };
    expect(parseRoute(routeToHash(route))).toEqual(route);
  });
});
