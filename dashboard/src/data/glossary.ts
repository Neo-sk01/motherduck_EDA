export const GLOSSARY: Record<string, string> = {
  reached_an_agent:
    "Share of calls that reached a live agent on the primary queue or after overflow.",
  right_language_routing:
    "Share of calls placed on the queue that matches the caller's spoken language.",
  missed_call_rate:
    "Share of calls that ended without ever reaching an agent.",
  untracked:
    "Calls present in raw logs but not assignable to a known outcome — usually log gaps.",
};

export function getGlossaryEntry(metricId: string | undefined): string | undefined {
  if (!metricId) return undefined;
  return GLOSSARY[metricId];
}
