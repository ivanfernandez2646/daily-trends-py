import { ApiError } from "../../api/client";
import { Notice } from "../../components/ui/notice";
import { isSessionEnd } from "./is-session-end";

/** A save that failed, with the API's reason when there is one; the form keeps its values. */
export function SaveError({ error }: { error: Error | null }) {
  if (error === null || isSessionEnd(error)) {
    return null;
  }
  return (
    <Notice tone="error">
      <p className="font-semibold">No se pudo guardar la noticia</p>
      {error instanceof ApiError && <p className="mt-1 text-caption">{error.message}</p>}
    </Notice>
  );
}
