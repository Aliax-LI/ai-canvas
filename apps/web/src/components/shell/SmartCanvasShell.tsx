import { Outlet } from "react-router-dom";

/** 智能画布全屏壳：无 Studio 侧栏，占满视口 */
export function SmartCanvasShell() {
  return (
    <div data-testid="smart-canvas-shell" className="flex h-full min-h-0 flex-col bg-background">
      <Outlet />
    </div>
  );
}
