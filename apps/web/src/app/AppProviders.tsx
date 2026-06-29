import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { CommandPalette } from "@/components/shell/CommandPalette";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function AppProviders() {
  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      <CommandPalette />
      <Toaster richColors closeButton position="top-right" />
    </QueryClientProvider>
  );
}
