import { DataPictureRenderer } from "@/components/DataPicture/DataPictureRenderer";
import { PromptBar } from "@/components/DataPicture/PromptBar";
import { ApiError, getDataPicture, getDataPictureExamples } from "@/lib/api";
import type { DataPicture } from "@/lib/api";

export const dynamic = "force-dynamic";

const DEFAULT_QUESTION = "Which universities lead in research income in 2024?";

export default async function DataPictureStudioPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const question = firstValue(query.q) || DEFAULT_QUESTION;
  const examples = await getDataPictureExamples();

  let picture: DataPicture | null = null;
  let composeError: string | null = null;
  try {
    picture = await getDataPicture(question);
  } catch (error) {
    composeError =
      error instanceof ApiError
        ? `That question couldn't be composed (${error.status}). Try rephrasing it or pick an example below.`
        : "Something went wrong composing that data picture.";
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Data Picture Studio</h1>
        <p className="mt-1 text-sm text-muted">
          Type a strategic question in plain English and get back a composed, evidence-backed data story: a
          headline insight, charts, evidence cards, caveats, and a full source trace.
        </p>
      </div>
      <section className="panel p-4">
        <PromptBar defaultQuestion={question} examples={examples} />
      </section>
      {composeError ? (
        <section className="panel border-coral/40 bg-coral/5 p-4 text-sm text-coral">{composeError}</section>
      ) : picture ? (
        <DataPictureRenderer picture={picture} />
      ) : null}
    </div>
  );
}

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
