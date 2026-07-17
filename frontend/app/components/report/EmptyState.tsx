import { MapPinOff } from "lucide-react";

export function EmptyState({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center">
      <MapPinOff className="mb-3 size-8 text-muted-foreground/60" />
      <p className="text-sm text-muted-foreground">
        {message || "暂无数据。采集完成后会显示在这里。"}
      </p>
    </div>
  );
}
