import { useMutation } from "@tanstack/react-query";
import { createFileRoute, Link, redirect, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { logIn } from "../api/auth";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/button";
import { Field } from "../components/ui/field";
import { Notice } from "../components/ui/notice";
import { safeRedirect } from "../features/session/redirect";
import { useSession } from "../features/session/session-context";

type LoginSearch = { redirect?: string };

type Credentials = { email: string; password: string };

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch =>
    typeof search.redirect === "string" ? { redirect: search.redirect } : {},
  beforeLoad: async ({ context: { session } }) => {
    await session.restore();
    if (session.state().status === "active") {
      throw redirect({ to: "/admin", replace: true });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const { redirect: target } = Route.useSearch();
  const navigate = useNavigate();
  const session = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Credentials>>({});
  const login = useMutation({
    mutationFn: async (credentials: Credentials) =>
      session.start(await logIn(credentials.email, credentials.password)),
    onSuccess: () => navigate({ href: safeRedirect(target), replace: true }),
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const credentials = { email: email.trim(), password };
    const next: Partial<Credentials> = {
      ...(credentials.email === "" && { email: "Escribe tu email" }),
      ...(credentials.password === "" && { password: "Escribe tu contraseña" }),
    };
    setErrors(next);
    if (Object.keys(next).length === 0) {
      login.mutate(credentials);
    }
  };

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-2">
      <aside className="hidden flex-col justify-between border-r border-rule bg-paper p-12 lg:flex">
        <Link to="/" className="font-serif text-masthead">
          Daily Trends
        </Link>
        <p className="max-w-md font-serif text-title-1">
          Los titulares de la prensa española, en un solo lugar.
        </p>
        <p className="text-caption text-meta">CMS · Acceso para administradores</p>
      </aside>

      <main className="flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm rounded-card border border-rule bg-surface p-8">
          <p className="text-label text-meta uppercase lg:hidden">
            <Link to="/" className="hover:text-accent">
              Daily Trends
            </Link>{" "}
            · CMS
          </p>
          <h1 className="mt-2 font-serif text-title-2 lg:mt-0">Accede al CMS</h1>
          <p className="mt-2 text-caption text-meta">
            Entra con la cuenta de administrador que te han dado.
          </p>

          <form noValidate onSubmit={submit} className="mt-6 flex flex-col gap-4">
            <Field
              label="Email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              error={errors.email}
            />
            <Field
              label="Contraseña"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={errors.password}
            />
            {login.isError && <LoginError error={login.error} />}
            <Button type="submit" disabled={login.isPending} className="mt-2">
              {login.isPending ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}

function LoginError({ error }: { error: Error }) {
  // The same answer for an unknown email and a wrong password, as the API gives.
  if (error instanceof ApiError && error.status === 401) {
    return <Notice tone="error">Email o contraseña incorrectos</Notice>;
  }
  return (
    <Notice tone="error">
      <p className="font-semibold">No se pudo iniciar sesión</p>
      {error instanceof ApiError && <p className="mt-1 text-caption">{error.message}</p>}
    </Notice>
  );
}
