import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

export default function ReportSkeleton() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 pb-12 sm:px-8">
        <div className="py-6 sm:py-8">
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="bg-muted px-5 py-6 sm:px-8 sm:py-8">
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="mt-4 h-8 w-2/3 rounded sm:h-10" />
                <div className="mt-4 flex gap-4">
                  <Skeleton className="h-4 w-24 rounded" />
                  <Skeleton className="h-4 w-32 rounded" />
                </div>
              </div>
              <div className="flex gap-2 px-5 py-3 sm:px-8">
                <Skeleton className="h-8 w-24 rounded" />
                <Skeleton className="h-8 w-32 rounded" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="-mx-4 border-b px-4 py-3 sm:-mx-8 sm:px-8">
          <div className="flex gap-2 overflow-hidden">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-20 shrink-0 rounded-full" />
            ))}
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-5">
                <Skeleton className="h-6 w-3/4 rounded" />
                <Skeleton className="mt-2 h-4 w-1/2 rounded" />
                <Skeleton className="mt-4 h-16 w-full rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}
