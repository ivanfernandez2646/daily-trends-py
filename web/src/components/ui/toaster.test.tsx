import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { type Toast, ToastProvider, useToast } from "./toaster";

afterEach(() => {
  vi.useRealTimers();
});

function ShowButton({ toast }: { toast: Toast }) {
  const { show } = useToast();
  return (
    <button type="button" onClick={() => show(toast)}>
      Mostrar
    </button>
  );
}

function renderToaster(toast: Toast) {
  render(
    <ToastProvider>
      <ShowButton toast={toast} />
    </ToastProvider>,
  );
  return screen.getByRole("button", { name: "Mostrar" });
}

it("announces a success as a status in the notices at the bottom", async () => {
  await userEvent.click(renderToaster({ tone: "success", message: "Noticia borrada" }));

  const notices = screen.getByRole("region", { name: "Avisos" });
  expect(within(notices).getByRole("status")).toHaveTextContent("Noticia borrada");
});

it("announces an error as an alert, with its detail", async () => {
  await userEvent.click(
    renderToaster({
      tone: "error",
      message: "No se pudieron actualizar las portadas",
      detail: "Internal server error",
    }),
  );

  const alert = screen.getByRole("alert");
  expect(alert).toHaveTextContent("No se pudieron actualizar las portadas");
  expect(alert).toHaveTextContent("Internal server error");
});

it("closes a notice on request", async () => {
  await userEvent.click(renderToaster({ tone: "error", message: "No se pudo borrar la noticia" }));

  await userEvent.click(screen.getByRole("button", { name: "Cerrar aviso" }));

  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("hides a success after a few seconds", () => {
  vi.useFakeTimers();
  render(
    <ToastProvider>
      <ShowButton toast={{ tone: "success", message: "Noticia borrada" }} />
    </ToastProvider>,
  );
  act(() => screen.getByRole("button", { name: "Mostrar" }).click());
  expect(screen.getByRole("status")).toBeInTheDocument();

  act(() => vi.advanceTimersByTime(6_000));

  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

it("keeps an error until it is closed", () => {
  vi.useFakeTimers();
  render(
    <ToastProvider>
      <ShowButton toast={{ tone: "error", message: "No se pudo borrar la noticia" }} />
    </ToastProvider>,
  );
  act(() => screen.getByRole("button", { name: "Mostrar" }).click());

  act(() => vi.advanceTimersByTime(60_000));

  expect(screen.getByRole("alert")).toBeInTheDocument();
});
