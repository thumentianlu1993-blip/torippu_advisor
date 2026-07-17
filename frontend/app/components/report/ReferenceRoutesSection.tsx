import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Route, Clock, Footprints } from "lucide-react";
import { EmptyState } from "./EmptyState";

export default function ReferenceRoutesSection({ content }: { content: any }) {
  const routes = content?.reference_routes || [];

  if (!routes.length) {
    return <EmptyState message="暂无参考路线。" />;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Route className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">参考路线</h2>
      </div>
      <div className="space-y-4">
        {routes.map((route: any, i: number) => (
          <Card key={route.id || i} className="editorial-shadow">
            <CardContent className="pt-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-heading text-lg font-semibold">{route.name || `Route ${i + 1}`}</h3>
                <div className="flex gap-2">
                  {route.duration && (
                    <Badge variant="secondary" className="text-xs">
                      <Clock className="mr-1 inline size-3" /> {route.duration}
                    </Badge>
                  )}
                  {route.distance && <Badge variant="outline" className="text-xs">{route.distance}</Badge>}
                </div>
              </div>
              {route.summary && (
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{route.summary}</p>
              )}
              {route.stops?.length > 0 && (
                <div className="mt-4">
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">停留点</h4>
                  <ol className="space-y-2">
                    {route.stops.map((stop: any, si: number) => (
                      <li key={si} className="flex items-start gap-3 rounded-lg bg-muted/40 p-3">
                        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-terracotta-100 text-xs font-bold text-terracotta-800">
                          {si + 1}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{typeof stop === "string" ? stop : stop.name}</p>
                          {stop.notes && (
                            <p className="text-xs text-muted-foreground">{stop.notes}</p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
