import { describe, expect, it } from "vitest";
import { formatPhone, humanizeAnomalyKind } from "./format";

describe("formatPhone", () => {
  it("formats a NANP number with leading +1", () => {
    expect(formatPhone("+19052833500")).toBe("+1 (905) 283-3500");
  });

  it("formats a 10-digit NANP number without country code", () => {
    expect(formatPhone("9052833500")).toBe("+1 (905) 283-3500");
  });

  it("returns the raw value for non-NANP input", () => {
    expect(formatPhone("442012345678")).toBe("442012345678");
    expect(formatPhone("")).toBe("");
    expect(formatPhone("anonymous")).toBe("anonymous");
  });
});

describe("humanizeAnomalyKind", () => {
  it("maps known anomaly kinds to plain sentences", () => {
    expect(humanizeAnomalyKind("volume_spike")).toBe("Volume spike");
    expect(humanizeAnomalyKind("volume_drop")).toBe("Volume drop");
    expect(humanizeAnomalyKind("cross_queue_caller")).toBe("Caller hit multiple queues");
    expect(humanizeAnomalyKind("no_agent_outlier")).toBe("Unusual missed-call rate");
    expect(humanizeAnomalyKind("routing_mismatch")).toBe("Wrong-language routing");
  });

  it("falls back to title-cased text for unknown kinds", () => {
    expect(humanizeAnomalyKind("some_new_kind")).toBe("Some New Kind");
  });
});
