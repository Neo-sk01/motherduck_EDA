import { describe, expect, it } from "vitest";
import { statusFor } from "./thresholds";

describe("statusFor", () => {
  it("returns good for reached_an_agent at or above 0.90", () => {
    expect(statusFor("reached_an_agent", 0.95)).toBe("good");
    expect(statusFor("reached_an_agent", 0.9)).toBe("good");
  });

  it("returns watch for reached_an_agent in the 0.80–0.90 band", () => {
    expect(statusFor("reached_an_agent", 0.85)).toBe("watch");
    expect(statusFor("reached_an_agent", 0.8)).toBe("watch");
  });

  it("returns at-risk for reached_an_agent below 0.80", () => {
    expect(statusFor("reached_an_agent", 0.79)).toBe("at-risk");
  });

  it("returns good for missed_call_rate at or below 0.05", () => {
    expect(statusFor("missed_call_rate", 0.05)).toBe("good");
    expect(statusFor("missed_call_rate", 0.02)).toBe("good");
  });

  it("returns watch for missed_call_rate between 0.05 and 0.10", () => {
    expect(statusFor("missed_call_rate", 0.08)).toBe("watch");
  });

  it("returns at-risk for missed_call_rate above 0.10", () => {
    expect(statusFor("missed_call_rate", 0.12)).toBe("at-risk");
  });

  it("returns good for right_language_routing at or above 0.95", () => {
    expect(statusFor("right_language_routing", 0.97)).toBe("good");
  });

  it("returns watch for right_language_routing between 0.85 and 0.95", () => {
    expect(statusFor("right_language_routing", 0.9)).toBe("watch");
  });

  it("returns at-risk for right_language_routing below 0.85", () => {
    expect(statusFor("right_language_routing", 0.8)).toBe("at-risk");
  });

  it("returns undefined for unknown metric ids", () => {
    expect(statusFor("unknown_metric", 0.5)).toBeUndefined();
  });
});
