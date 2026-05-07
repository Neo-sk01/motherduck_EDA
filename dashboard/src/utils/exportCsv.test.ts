import { describe, expect, it } from "vitest";
import { toCsv } from "./exportCsv";

describe("toCsv", () => {
  it("serializes headers in the requested order", () => {
    const csv = toCsv([{ name: "Gabriel", total: 299 }], [
      { key: "total", header: "Total" },
      { key: "name", header: "Agent" },
    ]);

    expect(csv.split("\n")[0]).toBe("Total,Agent");
    expect(csv.split("\n")[1]).toBe("299,Gabriel");
  });

  it("escapes commas, quotes, and newlines", () => {
    const csv = toCsv([{ value: "A, \"quoted\"\ncell" }], [
      { key: "value", header: "Value" },
    ]);

    expect(csv).toBe('Value\n"A, ""quoted""\ncell"');
  });

  it("serializes nullish values as blank cells", () => {
    const csv = toCsv([{ name: null, count: undefined }], [
      { key: "name", header: "Name" },
      { key: "count", header: "Count" },
    ]);

    expect(csv).toBe("Name,Count\n,");
  });
});
