import { createContext, useContext } from "react";

interface CanvasEditorActions {
  updateNodeData: (nodeId: string, patch: Record<string, unknown>) => void;
}

const CanvasEditorActionsContext = createContext<CanvasEditorActions | null>(null);

export function CanvasEditorActionsProvider({
  value,
  children,
}: {
  value: CanvasEditorActions;
  children: React.ReactNode;
}) {
  return (
    <CanvasEditorActionsContext.Provider value={value}>{children}</CanvasEditorActionsContext.Provider>
  );
}

export function useCanvasEditorActions(): CanvasEditorActions {
  const ctx = useContext(CanvasEditorActionsContext);
  if (!ctx) throw new Error("useCanvasEditorActions must be used within provider");
  return ctx;
}
