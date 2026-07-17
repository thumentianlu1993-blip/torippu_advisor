import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Compass, MapPin } from "lucide-react";
import { EmptyState } from "./EmptyState";

export default function CoreExperiencesSection({ content }: { content: any }) {
  const items = content?.core_experiences || [];

  if (!items.length) {
    return <EmptyState message="暂无核心体验。采集完成后会显示在这里。" />;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Compass className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">核心体验</h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item: any, i: number) => (
          <Card key={i} className="editorial-shadow">
            <CardContent className="pt-5">
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex size-8 items-center justify-center rounded-full bg-terracotta-50 text-terracotta-700">
                  <Compass className="size-4" />
                </div>
                {item.category && (
                  <Badge variant="secondary" className="text-xs">{item.category}</Badge>
                )}
              </div>
              <h3 className="font-heading text-lg font-semibold">{item.name}</h3>
              {item.area && (
                <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="size-3" /> {item.area}
                </p>
              )}
              {item.reason && (
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{item.reason}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
