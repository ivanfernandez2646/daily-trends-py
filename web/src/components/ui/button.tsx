import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap transition-colors duration-150 ease-out disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-ink text-surface hover:bg-ink-soft",
        secondary: "border border-field-border bg-surface text-ink hover:bg-canvas",
        destructive: "bg-danger text-surface hover:opacity-90",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-11 px-5",
        dense: "h-10 px-4 text-sm",
        icon: "size-11 [&_svg]:size-5",
      },
    },
    compoundVariants: [{ variant: "link", className: "h-auto min-h-11 px-0" }],
    defaultVariants: { variant: "primary", size: "default" },
  },
);

type ButtonProps = ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    /** Style the only child, such as a link, as a button instead of rendering a `button`. */
    asChild?: boolean;
  };

export function Button({
  className,
  variant = "primary",
  size,
  asChild = false,
  type,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot.Root : "button";
  return (
    <Component
      data-slot="button"
      data-variant={variant}
      className={cn(buttonVariants({ variant, size }), className)}
      type={asChild ? type : (type ?? "button")}
      {...props}
    />
  );
}

type IconButtonProps = Omit<ButtonProps, "size" | "children" | "aria-label"> & {
  /** What the button does: an icon alone is not a name. */
  label: string;
  children: ReactNode;
};

export function IconButton({ label, variant = "link", className, ...props }: IconButtonProps) {
  return (
    <Button
      aria-label={label}
      variant={variant}
      size="icon"
      className={cn(variant === "link" && "px-0 text-ink hover:text-accent", className)}
      {...props}
    />
  );
}
