import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { fetchApiProviders, type RunningHubAppEntry } from "../../api";
import { useCanvasEditorActions } from "../EditorActionsContext";
import { NodeRunActions } from "../NodeRunActions";
import { runRhNode, type RunNodeRuntime } from "../../lib/runNode";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { RhNodeData } from "@infinite-canvas/canvas-schema";

function entryId(entry: RunningHubAppEntry, kind: "app" | "workflow"): string {
  return String(kind === "workflow" ? entry.workflowId || entry.id : entry.appId || entry.id || "").trim();
}

function entryLabel(entry: RunningHubAppEntry, kind: "app" | "workflow"): string {
  const id = entryId(entry, kind);
  return entry.title || entry.name || (kind === "workflow" ? `工作流 ${id.slice(-6)}` : `应用 ${id.slice(-6)}`);
}

export function RhNode({ id, data, selected }: CanvasNodeProps<RhNodeData>) {
  const { nodes, edges, updateNodeData, appendLog, writeOutputImages } = useCanvasEditorActions();
  const [running, setRunning] = useState(Boolean(data.running));
  const rhMode = String(data.rhMode ?? "app");
  const webappId = String(data.webappId ?? "");
  const workflowId = String(data.workflowId ?? "");
  const rhPayment = String(data.rhPayment ?? "free");
  const runError = String(data.runError ?? "");
  const cascadeIdx = String(data._cascadeIdx ?? "");
  const rhParams = (data.rhParams ?? {}) as Record<string, unknown>;
  const rhParamsJson = useMemo(() => JSON.stringify(rhParams, null, 2), [rhParams]);

  const providersQuery = useQuery({
    queryKey: ["api-providers"],
    queryFn: fetchApiProviders,
    staleTime: 60_000,
  });

  const rhProvider = useMemo(
    () => (providersQuery.data ?? []).find((p) => p.id === "runninghub"),
    [providersQuery.data],
  );

  const appEntries = useMemo(
    () => (rhProvider?.rh_apps ?? []).filter((e) => e.enabled !== false && e.hidden !== true),
    [rhProvider],
  );
  const workflowEntries = useMemo(
    () => (rhProvider?.rh_workflows ?? []).filter((e) => e.enabled !== false && e.hidden !== true),
    [rhProvider],
  );

  const selectedKey = rhMode === "workflow" ? workflowId : webappId;

  useEffect(() => {
    if (selectedKey) return;
    const first = rhMode === "workflow" ? workflowEntries[0] : appEntries[0];
    if (!first) return;
    const eid = entryId(first, rhMode === "workflow" ? "workflow" : "app");
    if (rhMode === "workflow") updateNodeData(id, { workflowId: eid });
    else updateNodeData(id, { webappId: eid });
  }, [selectedKey, rhMode, appEntries, workflowEntries, id, updateNodeData]);

  const runtime = useMemo<RunNodeRuntime>(
    () => ({
      nodes,
      edges,
      getNodes: () => nodes,
      getEdges: () => edges,
      updateNodeData,
      appendLog,
      writeOutputImages,
    }),
    [nodes, edges, updateNodeData, appendLog, writeOutputImages],
  );

  const nodeRef = useMemo(
    () => ({ id, data, type: "rh" as const, position: { x: 0, y: 0 } }),
    [id, data],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      await runRhNode(nodeRef, runtime);
      toast.success("RunningHub 任务完成");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "RunningHub 运行失败");
    } finally {
      setRunning(false);
    }
  }, [nodeRef, runtime]);

  const handleEntryChange = useCallback(
    (value: string) => {
      const [kind, eid] = value.split(":");
      if (kind === "workflow") {
        updateNodeData(id, { rhMode: "workflow", workflowId: eid, webappId: "" });
      } else {
        updateNodeData(id, { rhMode: "app", webappId: eid, workflowId: "" });
      }
    },
    [id, updateNodeData],
  );

  const selectValue =
    rhMode === "workflow" && workflowId
      ? `workflow:${workflowId}`
      : webappId
        ? `app:${webappId}`
        : "";

  return (
    <BaseNodeShell
      type="rh"
      title="RunningHub"
      selected={selected}
      running={running}
      data-testid={`canvas-node-${id}`}
    >
      <div className="space-y-2 nodrag">
        <div>
          <Label className="text-xs text-muted-foreground">模式</Label>
          <select
            className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
            value={rhMode}
            onChange={(e) => updateNodeData(id, { rhMode: e.target.value })}
          >
            <option value="app">AI 应用</option>
            <option value="workflow">工作流</option>
          </select>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">
            {rhMode === "workflow" ? "工作流" : "应用"}
          </Label>
          <select
            className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
            value={selectValue}
            onChange={(e) => handleEntryChange(e.target.value)}
            data-testid={`canvas-rh-app-select-${id}`}
          >
            <option value="">选择…</option>
            {rhMode === "app"
              ? appEntries.map((entry) => {
                  const eid = entryId(entry, "app");
                  return (
                    <option key={eid} value={`app:${eid}`}>
                      {entryLabel(entry, "app")}
                    </option>
                  );
                })
              : workflowEntries.map((entry) => {
                  const eid = entryId(entry, "workflow");
                  return (
                    <option key={eid} value={`workflow:${eid}`}>
                      {entryLabel(entry, "workflow")}
                    </option>
                  );
                })}
          </select>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">计费</Label>
          <select
            className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
            value={rhPayment}
            onChange={(e) => updateNodeData(id, { rhPayment: e.target.value })}
          >
            <option value="free">免费额度</option>
            <option value="wallet">钱包</option>
          </select>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">rhParams (JSON)</Label>
          <Textarea
            value={rhParamsJson}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value || "{}") as Record<string, unknown>;
                updateNodeData(id, { rhParams: parsed });
              } catch {
                /* 编辑中允许无效 JSON */
              }
            }}
            className="min-h-[72px] font-mono text-[10px]"
          />
        </div>
        {cascadeIdx ? <p className="text-xs text-muted-foreground">级联 {cascadeIdx}</p> : null}
        {runError ? <p className="text-xs text-destructive">{runError}</p> : null}
        <NodeRunActions
          nodeId={id}
          running={running}
          onRun={handleRun}
          runTestId={`canvas-rh-run-${id}`}
        />
      </div>
    </BaseNodeShell>
  );
}
