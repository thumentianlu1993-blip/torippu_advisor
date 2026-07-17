import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Wallet, TrendingUp, PiggyBank } from "lucide-react";
import { EmptyState } from "./EmptyState";

export default function BudgetSection({ content }: { content: any }) {
  const budget = content?.budget || {};
  const entries = Object.entries(budget).filter(([_, value]) => value !== undefined && value !== null);

  if (!entries.length) {
    return <EmptyState message="暂无预算估算。" />;
  }

  const total = budget.total || budget.total_estimate;
  const perPerson = budget.per_person || budget.per_person_estimate;
  const breakdown = budget.breakdown || budget.items;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Wallet className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">预算估算</h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {total && (
          <Card className="editorial-shadow">
            <CardContent className="pt-5">
              <div className="flex items-center gap-2 text-muted-foreground">
                <TrendingUp className="size-4" />
                <span className="text-xs uppercase tracking-wide">总预算</span>
              </div>
              <p className="mt-2 font-heading text-2xl font-bold">{total}</p>
            </CardContent>
          </Card>
        )}
        {perPerson && (
          <Card className="editorial-shadow">
            <CardContent className="pt-5">
              <div className="flex items-center gap-2 text-muted-foreground">
                <PiggyBank className="size-4" />
                <span className="text-xs uppercase tracking-wide">人均</span>
              </div>
              <p className="mt-2 font-heading text-2xl font-bold">{perPerson}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {breakdown && (
        <Card className="editorial-shadow">
          <CardContent className="pt-5">
            <h3 className="mb-3 font-heading text-base font-semibold">明细</h3>
            <div className="space-y-2">
              {Array.isArray(breakdown) ? (
                breakdown.map((item: any, i: number) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2 text-sm"
                  >
                    <span className="font-medium">{item.category || item.name || "项目"}</span>
                    <Badge variant="outline">{item.amount || item.estimate || "—"}</Badge>
                  </div>
                ))
              ) : (
                Object.entries(breakdown).map(([key, value]: [string, any]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2 text-sm"
                  >
                    <span className="font-medium capitalize">{key.replace(/_/g, " ")}</span>
                    <Badge variant="outline">{String(value)}</Badge>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {budget.notes && (
        <p className="text-sm leading-relaxed text-muted-foreground">{budget.notes}</p>
      )}
    </div>
  );
}
