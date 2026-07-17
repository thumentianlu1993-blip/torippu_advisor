import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UtensilsCrossed, Clock, Banknote } from "lucide-react";
import { EmptyState } from "./EmptyState";

function RestaurantCard({ place }: { place: any }) {
  return (
    <Card className="overflow-hidden editorial-shadow">
      <CardContent className="p-0">
        <div className="flex">
          <div className="flex w-full flex-col p-4">
            <div className="flex items-start justify-between gap-2">
              <h4 className="font-heading text-base font-semibold">{place.name}</h4>
              {place.price_level !== undefined && place.price_level !== null && (
                <span className="shrink-0 text-xs text-muted-foreground">{"$".repeat(Number(place.price_level) + 1)}</span>
              )}
            </div>
            {place.cuisine && (
              <div className="mt-2 flex flex-wrap gap-1">
                {place.cuisine.split(",").map((c: string) => (
                  <Badge key={c} variant="outline" className="text-xs">{c.trim()}</Badge>
                ))}
              </div>
            )}
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
              {place.rating && (
                <span className="inline-flex items-center gap-1">⭐ {place.rating}</span>
              )}
              {place.area && <span>{place.area}</span>}
            </div>
            {(place.opening_hours || place.reservation_note) && (
              <div className="mt-3 space-y-1 border-t pt-3 text-xs text-muted-foreground">
                {place.opening_hours && (
                  <p className="flex items-center gap-1">
                    <Clock className="size-3" /> {place.opening_hours}
                  </p>
                )}
                {place.reservation_note && (
                  <p className="flex items-center gap-1">
                    <Banknote className="size-3" /> {place.reservation_note}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PoolSection({ title, subtitle, places }: { title: string; subtitle: string; places: any[] }) {
  if (!places?.length) return null;
  return (
    <div className="space-y-3">
      <div>
        <h3 className="font-heading text-lg font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {places.map((place: any, i: number) => (
          <RestaurantCard key={place.id || i} place={place} />
        ))}
      </div>
    </div>
  );
}

export default function FoodSection({ content }: { content: any }) {
  const food = content?.food || {};
  const reservationPool = food.reservation_pool || [];
  const randomPool = food.random_pool || [];

  if (!reservationPool.length && !randomPool.length) {
    return <EmptyState message="暂无美食推荐。" />;
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <UtensilsCrossed className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">美食与餐厅</h2>
      </div>
      <PoolSection
        title="值得预订"
        subtitle="人气餐厅，建议提前订位"
        places={reservationPool}
      />
      <PoolSection
        title="随性选择"
        subtitle="不用预约也能吃到的好选择"
        places={randomPool}
      />
    </div>
  );
}
