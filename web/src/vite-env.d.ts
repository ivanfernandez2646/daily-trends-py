/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The API origin for a build; absent, the app calls its own origin. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
