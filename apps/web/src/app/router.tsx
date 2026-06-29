import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppProviders } from "@/app/AppProviders";
import { ProductShell } from "@/components/shell/ProductShell";
import { CanvasShell } from "@/components/shell/CanvasShell";
import { StudioHomePage } from "@/features/studio/StudioHomePage";
import { CanvasListPage } from "@/features/canvas/CanvasListPage";
import { CanvasEditorPage } from "@/features/canvas/CanvasEditorPage";
import { SmartCanvasPage } from "@/features/smart-canvas/SmartCanvasPage";
import { AssetsPage } from "@/features/assets/AssetsPage";
import { ApiSettingsPage } from "@/features/settings/ApiSettingsPage";
import { ComfyuiSettingsPage } from "@/features/settings/ComfyuiSettingsPage";
import { ChatPage } from "@/features/chat/ChatPage";
import {
  AngleToolPage,
  EnhanceToolPage,
  KleinToolPage,
  OnlineToolPage,
  ZImageToolPage,
} from "@/features/tools/ToolsPages";

export const router = createBrowserRouter([
  {
    element: <AppProviders />,
    children: [
      {
        element: <ProductShell />,
        children: [
          { index: true, element: <StudioHomePage /> },
          { path: "canvases", element: <CanvasListPage /> },
          { path: "smart/:id", element: <SmartCanvasPage /> },
          { path: "assets", element: <AssetsPage /> },
          { path: "settings/api", element: <ApiSettingsPage /> },
          { path: "settings/comfyui", element: <ComfyuiSettingsPage /> },
          { path: "chat", element: <ChatPage /> },
          { path: "tools/zimage", element: <ZImageToolPage /> },
          { path: "tools/enhance", element: <EnhanceToolPage /> },
          { path: "tools/klein", element: <KleinToolPage /> },
          { path: "tools/online", element: <OnlineToolPage /> },
          { path: "tools/angle", element: <AngleToolPage /> },
        ],
      },
      {
        path: "canvas/:id",
        element: <CanvasShell />,
        children: [{ index: true, element: <CanvasEditorPage /> }],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
