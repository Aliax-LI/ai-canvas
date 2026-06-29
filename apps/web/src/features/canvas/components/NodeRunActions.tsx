import { GitBranch, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCanvasEditorActions } from "./EditorActionsContext";

interface NodeRunActionsProps {
  nodeId: string;
  running: boolean;
  onRun: () => void | Promise<void>;
  runTestId?: string;
  showCascade?: boolean;
  cascadeTestId?: string;
}

export function NodeRunActions({
  nodeId,
  running,
  onRun,
  runTestId,
  showCascade = true,
  cascadeTestId,
}: NodeRunActionsProps) {
  const { runCascade, cascadeRunning } = useCanvasEditorActions();

  return (
    <div className="flex gap-1">
      <Button
        type="button"
        size="sm"
        className="flex-1"
        disabled={running || cascadeRunning}
        data-testid={runTestId}
        onClick={() => void onRun()}
      >
        {running ? <Loader2 className="mr-1 size-3 animate-spin" /> : <Play className="mr-1 size-3" />}
        运行
      </Button>
      {showCascade ? (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="flex-1"
          disabled={running || cascadeRunning}
          data-testid={cascadeTestId ?? `canvas-cascade-run-${nodeId}`}
          onClick={() => void runCascade(nodeId)}
        >
          {cascadeRunning ? (
            <Loader2 className="mr-1 size-3 animate-spin" />
          ) : (
            <GitBranch className="mr-1 size-3" />
          )}
          级联
        </Button>
      ) : null}
    </div>
  );
}
