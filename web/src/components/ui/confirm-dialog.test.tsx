import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, it } from "vitest";
import { ConfirmDialog } from "./confirm-dialog";

/** A dialog opened from a button, recording every confirmation. */
function Harness({ confirmations }: { confirmations: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Borrar
      </button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="¿Borrar esta noticia?"
        description="Esta acción no se puede deshacer."
        confirmLabel="Borrar noticia"
        onConfirm={() => confirmations.push("confirmed")}
      >
        <p>El alquiler sube por tercer trimestre</p>
      </ConfirmDialog>
    </>
  );
}

async function openDialog(confirmations: string[] = []) {
  render(<Harness confirmations={confirmations} />);
  await userEvent.click(screen.getByRole("button", { name: "Borrar" }));
  return screen.getByRole("alertdialog", { name: "¿Borrar esta noticia?" });
}

it("asks with its title, description and content, with the focus inside", async () => {
  const dialog = await openDialog();

  expect(dialog).toHaveAccessibleDescription("Esta acción no se puede deshacer.");
  expect(dialog).toHaveTextContent("El alquiler sube por tercer trimestre");
  expect(dialog).toContainElement(document.activeElement as HTMLElement);
});

it("confirms with a destructive button", async () => {
  const confirmations: string[] = [];
  await openDialog(confirmations);

  const confirm = screen.getByRole("button", { name: "Borrar noticia" });
  expect(confirm).toHaveAttribute("data-variant", "destructive");
  await userEvent.click(confirm);

  expect(confirmations).toEqual(["confirmed"]);
});

it.each([
  ["Cancelar", () => userEvent.click(screen.getByRole("button", { name: "Cancelar" }))],
  ["Escape", () => userEvent.keyboard("{Escape}")],
])("closes with %s without confirming", async (_name, close) => {
  const confirmations: string[] = [];
  await openDialog(confirmations);

  await close();

  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(confirmations).toEqual([]);
  await waitFor(() => expect(screen.getByRole("button", { name: "Borrar" })).toHaveFocus());
});

it("disables its confirmation and says so while it is pending", () => {
  render(
    <ConfirmDialog
      open
      onOpenChange={() => {}}
      title="¿Borrar esta noticia?"
      description="Esta acción no se puede deshacer."
      confirmLabel="Borrar"
      pendingLabel="Borrando…"
      pending
      onConfirm={() => {}}
    />,
  );

  expect(screen.getByRole("button", { name: "Borrando…" })).toBeDisabled();
});
