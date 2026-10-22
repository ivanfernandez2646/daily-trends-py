import { createFileRoute, useBlocker, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { useFeedForEditing, useUpdateFeed } from "../api/feeds";
import type { FeedResponse } from "../api/types";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { Skeleton } from "../components/ui/skeleton";
import { type Toast, useToast } from "../components/ui/toaster";
import { DeleteFeedDialog } from "../features/admin/delete-feed-dialog";
import { FeedForm } from "../features/admin/feed-form";
import {
  type FeedFormValues,
  formFromFeed,
  previewFeed,
  toUpdateRequest,
  validateFeedForm,
} from "../features/admin/feed-form-values";
import { SaveError } from "../features/admin/save-error";
import { LoadError } from "../features/feeds/load-error";

export const Route = createFileRoute("/admin/feeds/$id/edit")({
  component: EditFeedPage,
});

const GONE: Toast = { tone: "error", message: "Esta noticia ya no existe" };

/** A 404, or a 400 for an id that is not a UUID: either way there is no feed to edit. */
function isGone(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 400);
}

/** Back to the list, with a notice when given; nothing is left to confirm before leaving. */
function useLeave() {
  const navigate = useNavigate();
  const { show } = useToast();
  return (toast?: Toast) => {
    if (toast !== undefined) {
      show(toast);
    }
    void navigate({ to: "/admin", ignoreBlocker: true });
  };
}

function EditFeedPage() {
  const { id } = Route.useParams();
  const feed = useFeedForEditing(id);
  const leave = useLeave();
  const left = useRef(false);
  const gone = isGone(feed.error);

  useEffect(() => {
    if (gone && !left.current) {
      left.current = true;
      leave(GONE);
    }
  }, [gone, leave]);

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6">
      <h1 className="font-serif text-title-1">Editar noticia</h1>
      {feed.data !== undefined && feed.isFetchedAfterMount ? (
        <EditFeedForm key={feed.data.id} feed={feed.data} />
      ) : feed.isError && !gone ? (
        <LoadError onRetry={() => void feed.refetch()} />
      ) : (
        <div
          role="status"
          className="flex flex-col gap-4 rounded-card border border-rule bg-surface p-6"
        >
          <span className="sr-only">Cargando la noticia</span>
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-10 w-2/3" />
        </div>
      )}
    </div>
  );
}

function EditFeedForm({ feed }: { feed: FeedResponse }) {
  const update = useUpdateFeed();
  const leave = useLeave();
  const [values, setValues] = useState<FeedFormValues>(() => formFromFeed(feed));
  const [submitted, setSubmitted] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const changes = toUpdateRequest(feed, values);
  const changed = Object.keys(changes).length > 0;
  // The author is not edited here, so it cannot be what is wrong.
  const { author: _author, ...errors } = submitted ? validateFeedForm(values) : {};

  const blocker = useBlocker({
    shouldBlockFn: () => changed,
    enableBeforeUnload: () => changed,
    withResolver: true,
  });

  const submit = () => {
    setSubmitted(true);
    if (values.title.trim() === "") {
      return;
    }
    update.mutate(
      { id: feed.id, changes },
      {
        onSuccess: () => leave({ tone: "success", message: "Cambios guardados" }),
        onError: (error) => {
          if (isGone(error)) {
            leave(GONE);
          }
        },
      },
    );
  };

  return (
    <>
      <FeedForm
        mode="edit"
        feed={feed}
        changed={changed}
        onDelete={() => setDeleting(true)}
        values={values}
        errors={errors}
        onChange={(change) => setValues((current) => ({ ...current, ...change }))}
        onSubmit={submit}
        submitLabel="Guardar cambios"
        pending={update.isPending}
        preview={previewFeed(values, feed)}
        error={<SaveError error={update.error} />}
      />
      <DeleteFeedDialog
        feed={deleting ? feed : undefined}
        onClose={() => setDeleting(false)}
        onDeleted={() => leave()}
      />
      <ConfirmDialog
        open={blocker.status === "blocked"}
        onOpenChange={(open) => !open && blocker.reset?.()}
        title="¿Salir sin guardar?"
        description="Los cambios que no has guardado se perderán."
        confirmLabel="Salir"
        cancelLabel="Seguir editando"
        onConfirm={() => blocker.proceed?.()}
      />
    </>
  );
}
