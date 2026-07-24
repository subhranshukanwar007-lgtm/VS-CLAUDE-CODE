"use client";

import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      theme="dark"
      position="top-right"
      toastOptions={{
        classNames: {
          toast: "glass-panel !text-foreground !border-border",
          title: "!text-foreground",
          description: "!text-muted-foreground",
        },
      }}
    />
  );
}
