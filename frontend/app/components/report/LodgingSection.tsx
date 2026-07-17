import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Hotel, MapPin, Star, Banknote } from "lucide-react";
import { EmptyState } from "./EmptyState";

export default function LodgingSection({ content }: { content: any }) {
  const lodgings = Array.isArray(content?.lodging)
    ? content.lodging
    : content?.lodging
      ? [content.lodging]
      : [];

  if (!lodgings.length) {
    return <EmptyState message="暂无住宿推荐。" />;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Hotel className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">住宿推荐</h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {lodgings.map((item: any, i: number) => (
          <Card key={item.id || i} className="editorial-shadow">
            <CardContent className="pt-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-heading text-lg font-semibold">{item.name || item.hotel_name || `Option ${i + 1}`}</h3>
                {item.price_level !== undefined && item.price_level !== null && (
                  <span className="text-xs text-muted-foreground">{"$".repeat(Number(item.price_level) + 1)}</span>
                )}
              </div>
              {item.area && (
                <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="size-3" /> {item.area}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {item.rating && (
                  <Badge variant="secondary" className="text-xs">
                    <Star className="mr-1 inline size-3" /> {item.rating}
                  </Badge>
                )}
                {item.type && <Badge variant="outline" className="text-xs">{item.type}</Badge>}
              </div>
              {item.summary && (
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{item.summary}</p>
              )}
              {item.price_estimate && (
                <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                  <Banknote className="size-3" /> {item.price_estimate}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
