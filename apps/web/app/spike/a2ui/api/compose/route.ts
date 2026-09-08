import { NextResponse } from "next/server";
import { catalogueById, loadCatalogue } from "@/lib/spike/catalogue";
import { buildComposition, DEFAULT_SURFACE_ID, resolveSelection } from "@/lib/spike/compose";
import { runSelection } from "@/lib/spike/select";
import type { ComposeRequest, ComposeResponse } from "@/lib/spike/types";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ComposeRequest;
    const messages = body.messages ?? [];
    const turn = messages.filter((message) => message.role === "user").length;
    const latestIntent = [...messages].reverse().find((message) => message.role === "user")?.content ?? "";

    const { entries, source: catalogueSource } = await loadCatalogue();
    const catalogue = catalogueById(entries);

    const { selection, selector } = await runSelection(messages, entries, body.priorSelection);
    const resolved = resolveSelection(selection, catalogue);

    const surfaceId = body.surfaceId ?? DEFAULT_SURFACE_ID;
    const { messages: a2uiMessages, compositionTree, dataSource } = await buildComposition(selection, catalogue, {
      surfaceId,
      isRefinement: body.isRefinement
    });

    const response: ComposeResponse = {
      selection,
      messages: a2uiMessages,
      log: {
        turn,
        intent: latestIntent,
        selector,
        rationale: selection.rationale,
        resolvedInsights: resolved,
        compositionTree,
        clarify: selection.clarify,
        unavailableNotes: selection.unavailableNotes,
        rawMessages: a2uiMessages,
        dataSource: dataSource === "mock_fallback" || catalogueSource === "mock_fallback" ? "mock_fallback" : "live_api"
      }
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("[spike/a2ui/compose]", error);
    return NextResponse.json({ error: "Compose failed" }, { status: 500 });
  }
}
