export default function CoverageStatus({ coverage, updatedAt, missing }: { coverage: "complete" | "partial" | "stale"; updatedAt?: string; missing: string[] }) {
  const labels = { complete: "覆盖完整", partial: "覆盖不完整", stale: "数据待更新" };
  return (
    <section className="mt-4 rounded-lg border bg-muted/30 p-4" aria-label="coverage status">
      <p className="font-medium">{labels[coverage] || labels.stale}</p>
      {updatedAt && <p className="text-xs text-muted-foreground">最近更新：{new Date(updatedAt).toLocaleString()}</p>}
      {missing.length > 0 && <p className="mt-1 text-sm">缺失类别：{missing.join("、")}</p>}
    </section>
  );
}
