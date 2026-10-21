import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Tinta's type scale: without it, `text-display` would read as a color and lose to `text-ink`.
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: ["masthead", "display", "title-1", "title-2", "lead", "body", "caption", "label"],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
