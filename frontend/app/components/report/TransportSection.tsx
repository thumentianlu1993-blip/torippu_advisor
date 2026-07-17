import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Train, Plane, Bus, Footprints } from "lucide-react";
import { EmptyState } from "./EmptyState";

const MODE_ICONS: Record<string, React.ElementType> = {
  train: Train,
  flight: Plane,
  bus: Bus,
  walk: Footprints,
  subway: Train,
  taxi: Bus,
  car: Bus,
};

export default function TransportSection({ content }: { content: any }) {
  const transport = content?.transport || {};
  const modes = Object.entries(transport).filter(([_, value]) => Array.isArray(value) && value.length);

  if (!modes.length) {
    return <EmptyState message="暂无交通详情。" />;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Train className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">交通方式</h2>
      </div>
      <div className="space-y-4">
        {modes.map(([mode, routes]: [string, any]) => {
          const Icon = MODE_ICONS[mode.toLowerCase()] || Train;
          return (
            <Card key={mode} className="editorial-shadow">
              <CardContent className="pt-5">
                <div className="mb-3 flex items-center gap-2">
                  <Icon className="size-4 text-terracotta-600" />
                  <h3 className="font-heading text-base font-semibold capitalize">{mode}</h3>
                </div>
                <ul className="space-y-2">
                  {routes.map((route: any, i: number) => (
                    <li key={i} className="rounded-lg bg-muted/40 p-3 text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{route.from || route.origin || "Start"}</span>
                        <span className="text-muted-foreground">→</span>
                        <span className="font-medium">{route.to || route.destination || "End"}</span>
                        {route.duration && <Badge variant="outline" className="text-xs">{route.duration}</Badge>}
                      </div>
                      {route.notes && (
                        <p className="mt-1 text-xs text-muted-foreground">{route.notes}</p>
                      )}
                    </li>
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
