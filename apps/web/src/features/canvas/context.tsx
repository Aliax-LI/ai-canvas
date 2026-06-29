import { createContext, useContext } from "react";
import type { SaveState } from "./types";

export interface CanvasShellState {
  title: string;
  saveState: SaveState;
  setTitle: (title: string) => void;
  setSaveState: (state: SaveState) => void;
}

const CanvasShellContext = createContext<CanvasShellState | null>(null);

export function CanvasShellProvider({
  value,
  children,
}: {
  value: CanvasShellState;
  children: React.ReactNode;
}) {
  return <CanvasShellContext.Provider value={value}>{children}</CanvasShellContext.Provider>;
}

export function useCanvasShell(): CanvasShellState {
  const ctx = useContext(CanvasShellContext);
  if (!ctx) throw new Error("useCanvasShell must be used within CanvasShellProvider");
  return ctx;
}
