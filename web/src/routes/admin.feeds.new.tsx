import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ApiError } from "../api/client";
import { useCreateFeed } from "../api/feeds";
import { useToast } from "../components/ui/toaster";
import { FeedForm } from "../features/admin/feed-form";
import {
  EMPTY_FEED_FORM,
  type FeedFormValues,
  previewFeed,
  toCreateRequest,
  validateFeedForm,
} from "../features/admin/feed-form-values";
import { SaveError } from "../features/admin/save-error";

export const Route = createFileRoute("/admin/feeds/new")({
  component: NewFeedPage,
});

function NewFeedPage() {
  const navigate = useNavigate();
  const { show } = useToast();
  const create = useCreateFeed();
  // The app names the feed; a taken id is unexpected, and the next attempt gets a new one.
  const [id, setId] = useState(() => crypto.randomUUID());
  const [values, setValues] = useState<FeedFormValues>(EMPTY_FEED_FORM);
  const [submitted, setSubmitted] = useState(false);

  const errors = submitted ? validateFeedForm(values) : {};

  const submit = () => {
    setSubmitted(true);
    const { category } = values;
    if (Object.keys(validateFeedForm(values)).length > 0 || category === undefined) {
      return;
    }
    create.mutate(
      { id, feed: toCreateRequest({ ...values, category }) },
      {
        onSuccess: () => {
          show({ tone: "success", message: "Noticia creada" });
          void navigate({ to: "/admin" });
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 409) {
            setId(crypto.randomUUID());
          }
        },
      },
    );
  };

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6">
      <h1 className="font-serif text-title-1">Nueva noticia</h1>
      <FeedForm
        mode="create"
        values={values}
        errors={errors}
        onChange={(change) => setValues((current) => ({ ...current, ...change }))}
        onSubmit={submit}
        submitLabel="Crear noticia"
        pending={create.isPending}
        preview={previewFeed(values, {
          id,
          source: "CMS",
          url: null,
          created_at: new Date().toISOString(),
          updated_at: null,
        })}
        error={<SaveError error={create.error} />}
      />
    </div>
  );
}
