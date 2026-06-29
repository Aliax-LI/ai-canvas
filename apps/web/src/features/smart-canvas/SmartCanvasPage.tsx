import { useParams } from "react-router-dom";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function SmartCanvasPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <PlaceholderPage
      title={`智能画布 ${id ?? ""}`}
      description="智能画布卡片布局，对应上游 smart-canvas.html。"
    />
  );
}
