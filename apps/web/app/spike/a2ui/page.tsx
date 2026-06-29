import { SpikeClient } from "./SpikeClient";

export const dynamic = "force-dynamic";

export default function A2uiSpikePage() {
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber/30 bg-amber/5 px-4 py-3 text-sm text-amber">
        Throwaway spike — isolated from the production dashboard. Read-only access to pre-computed insights only; no metric
        derivation or shared mutable state.
      </div>
      <div>
        <h1 className="text-2xl font-semibold">Generative insight composition (A2UI)</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Describe the insights and layout you want in plain language. An agent selects from the fixed catalogue and emits an
          A2UI composition rendered below. Inspect the log to verify intent → selection → composition.
        </p>
      </div>
      <SpikeClient />
    </div>
  );
}
