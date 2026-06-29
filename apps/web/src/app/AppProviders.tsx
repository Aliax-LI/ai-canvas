import { Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { CommandPalette } from "@/components/shell/CommandPalette";

export function AppProviders() {
  return (
    <>
      <Outlet />
      <CommandPalette />
      <Toaster richColors closeButton position="top-right" />
    </>
  );
}
