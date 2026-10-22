import { Link } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { type FormEvent, type ReactNode, useId } from "react";
import type { FeedResponse } from "../../api/types";
import { Button } from "../../components/ui/button";
import { Field, TextareaField } from "../../components/ui/field";
import { sourceLabel } from "../../lib/labels";
import { shortenArticleUrl } from "../../lib/urls";
import { FeedCard } from "../feeds/feed-card";
import { CategoryPicker } from "./category-picker";
import type { FeedFormErrors, FeedFormValues } from "./feed-form-values";

type FeedFormProps = {
  values: FeedFormValues;
  errors: FeedFormErrors;
  onChange: (change: Partial<FeedFormValues>) => void;
  onSubmit: () => void;
  submitLabel: string;
  pending: boolean;
  /** The feed as the front page would show it. */
  preview: FeedResponse;
  /** Why the last save failed, shown above the actions. */
  error?: ReactNode;
} & (
  | { mode: "create" }
  | {
      mode: "edit";
      /** The stored feed: its author, newspaper and link are shown, not edited. */
      feed: FeedResponse;
      /** Whether anything changed, so that saving would send something. */
      changed: boolean;
      onDelete: () => void;
    }
);

/** The fields of a feed, checked by the app before sending, next to a live preview of its card. */
export function FeedForm(props: FeedFormProps) {
  const { values, errors, onChange, onSubmit, submitLabel, pending, preview, error } = props;
  const previewId = useId();
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form
      noValidate
      onSubmit={submit}
      className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start"
    >
      <div className="flex flex-col gap-5 rounded-card border border-rule bg-surface p-5 sm:p-6">
        <Field
          label="Titular"
          value={values.title}
          onChange={(event) => onChange({ title: event.target.value })}
          error={errors.title}
        />
        <TextareaField
          label="Entradilla (opcional)"
          value={values.description}
          onChange={(event) => onChange({ description: event.target.value })}
        />
        {props.mode === "create" ? (
          <Field
            label="Autor"
            value={values.author}
            onChange={(event) => onChange({ author: event.target.value })}
            error={errors.author}
          />
        ) : (
          <FixedDetails feed={props.feed} />
        )}
        <CategoryPicker
          category={values.category}
          onChange={(category) => onChange({ category })}
          error={errors.category}
        />
        {error}
        <div className="flex flex-wrap gap-3 border-t border-rule pt-5">
          <Button type="submit" disabled={pending || (props.mode === "edit" && !props.changed)}>
            {pending ? "Guardando…" : submitLabel}
          </Button>
          <Button asChild variant="secondary">
            <Link to="/admin">Cancelar</Link>
          </Button>
          {props.mode === "edit" && (
            <Button variant="link" className="ml-auto text-danger" onClick={props.onDelete}>
              <Trash2 aria-hidden="true" />
              Borrar noticia
            </Button>
          )}
        </div>
      </div>

      <section
        aria-labelledby={previewId}
        className="flex flex-col gap-2 rounded-card border border-rule bg-paper p-5 lg:sticky lg:top-8"
      >
        <h2 id={previewId} className="text-label text-meta uppercase">
          Así se verá en la portada
        </h2>
        <FeedCard feed={preview} variant="grid" linked={false} />
      </section>
    </form>
  );
}

/** What a feed keeps from when it was written or scraped (S04, S09). */
function FixedDetails({ feed }: { feed: FeedResponse }) {
  return (
    <fieldset className="flex flex-col gap-3 rounded-field bg-canvas p-4 text-sm">
      <legend className="sr-only">No se puede cambiar</legend>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5">
        <dt className="text-meta">Autor</dt>
        <dd className="text-ink">{feed.author}</dd>
        <dt className="text-meta">Periódico</dt>
        <dd className="text-ink">{sourceLabel(feed.source)}</dd>
        <dt className="text-meta">Enlace</dt>
        <dd className="min-w-0 truncate">
          {feed.url === null ? (
            <span className="text-meta">Sin enlace</span>
          ) : (
            <a
              href={feed.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              {Object.values(shortenArticleUrl(feed.url)).join("")}
            </a>
          )}
        </dd>
      </dl>
      <p className="text-caption text-meta">
        El autor, el periódico y el enlace no se pueden cambiar.
      </p>
    </fieldset>
  );
}
