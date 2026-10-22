import { useDeleteFeed } from "../../api/feeds";
import type { FeedResponse } from "../../api/types";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { Notice } from "../../components/ui/notice";
import { useToast } from "../../components/ui/toaster";
import { isSessionEnd } from "./is-session-end";

type DeleteFeedDialogProps = {
  /** The feed to delete; the dialog is open while there is one. */
  feed: FeedResponse | undefined;
  onClose: () => void;
  onDeleted?: () => void;
};

export function DeleteFeedDialog({ feed, onClose, onDeleted }: DeleteFeedDialogProps) {
  const deletion = useDeleteFeed();
  const { show } = useToast();

  const close = () => {
    deletion.reset();
    onClose();
  };
  const confirm = () => {
    if (feed === undefined) {
      return;
    }
    deletion.mutate(feed.id, {
      onSuccess: () => {
        show({ tone: "success", message: "Noticia borrada" });
        close();
        onDeleted?.();
      },
    });
  };

  return (
    <ConfirmDialog
      open={feed !== undefined}
      onOpenChange={(open) => !open && close()}
      title="¿Borrar esta noticia?"
      description="Esta acción no se puede deshacer."
      confirmLabel="Borrar"
      pendingLabel="Borrando…"
      pending={deletion.isPending}
      onConfirm={confirm}
    >
      <p className="font-serif text-lead">{feed?.title}</p>
      {deletion.isError && !isSessionEnd(deletion.error) && (
        <Notice tone="error">
          <p className="font-semibold">No se pudo borrar la noticia</p>
          <p className="mt-1 text-caption">{deletion.error.message}</p>
        </Notice>
      )}
    </ConfirmDialog>
  );
}
