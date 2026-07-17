import { Card, CardContent } from "@/components/ui/card";
import { Lightbulb, ShieldCheck, Luggage, Clock } from "lucide-react";
import { EmptyState } from "./EmptyState";

const TIP_CATEGORIES: Record<string, { icon: React.ElementType; title: string }> = {
  general: { icon: Lightbulb, title: "通用建议" },
  safety: { icon: ShieldCheck, title: "安全" },
  packing: { icon: Luggage, title: "行李" },
  timing: { icon: Clock, title: "最佳时间" },
};

export default function TipsSection({ content }: { content: any }) {
  const tips = content?.tips || {};

  if (Array.isArray(tips) && !tips.length) {
    return <EmptyState message="暂无旅行贴士。" />;
  }

  if (!Array.isArray(tips) && typeof tips === "object" && !Object.keys(tips).length) {
    return <EmptyState message="暂无旅行贴士。" />;
  }

  if (Array.isArray(tips)) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-2 text-terracotta-700">
          <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
            <Lightbulb className="size-4" />
          </div>
          <h2 className="font-heading text-xl font-semibold">旅行贴士</h2>
        </div>
        <div className="grid gap-3">
          {tips.map((tip: any, i: number) => (
            <Card key={i} className="editorial-shadow">
              <CardContent className="py-4">
                <p className="text-sm leading-relaxed text-muted-foreground">{typeof tip === "string" ? tip : tip.text || tip.content}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Lightbulb className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">旅行贴士</h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(tips).map(([key, value]: [string, any]) => {
          const config = TIP_CATEGORIES[key] || { icon: Lightbulb, title: key };
          const Icon = config.icon;
          const items = Array.isArray(value) ? value : [value];
          return (
            <Card key={key} className="editorial-shadow">
              <CardContent className="pt-5">
                <div className="mb-3 flex items-center gap-2">
                  <Icon className="size-4 text-terracotta-600" />
                  <h3 className="font-heading text-base font-semibold capitalize">{config.title}</h3>
                </div>
                <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                  {items.map((item: any, i: number) => (
                    <li key={i}>{typeof item === "string" ? item : item.text || item.content}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
