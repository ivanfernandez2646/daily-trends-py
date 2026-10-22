import { Link } from "@tanstack/react-router";
import { type FormEvent, type ReactNode, useId } from "react";
import type { FeedResponse } from "../../api/types";
import { Button } from "../../components/ui/button";
import { Field, TextareaField } from "../../components/ui/field";
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
};

/** The fields of a feed, checked by the app before sending, next to a live preview of its card. */
export function FeedForm({
  values,
  errors,
  onChange,
  onSubmit,
  submitLabel,
  pending,
  preview,
  error,
}: FeedFormProps) {
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
        <Field
          label="Autor"
          value={values.author}
          onChange={(event) => onChange({ author: event.target.value })}
          error={errors.author}
        />
        <CategoryPicker
          category={values.category}
          onChange={(category) => onChange({ category })}
          error={errors.category}
        />
        {error}
        <div className="flex flex-wrap gap-3 border-t border-rule pt-5">
          <Button type="submit" disabled={pending}>
            {pending ? "Guardando…" : submitLabel}
          </Button>
          <Button asChild variant="secondary">
            <Link to="/admin">Cancelar</Link>
          </Button>
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
