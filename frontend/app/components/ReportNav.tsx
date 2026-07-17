"use client";

import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

const SECTIONS = [
  { key: "core_experiences", label: "核心" },
  { key: "important_experiences", label: "重要" },
  { key: "food", label: "美食" },
  { key: "lodging", label: "住宿" },
  { key: "transport", label: "交通" },
  { key: "budget", label: "预算" },
  { key: "tips", label: "贴士" },
  { key: "reference_routes", label: "路线" },
];

export default function ReportNav({ active, onSelect }: { active: string; onSelect: (key: string) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  };

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkScroll, { passive: true });
    window.addEventListener("resize", checkScroll);
    return () => {
      el.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
    };
  }, []);

  const scroll = (direction: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: direction === "left" ? -160 : 160, behavior: "smooth" });
  };

  return (
    <div className="sticky top-0 z-30 -mx-4 border-b bg-background/95 px-4 py-3 backdrop-blur-sm sm:-mx-8 sm:px-8">
      <div className="relative flex items-center">
        {canScrollLeft && (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => scroll("left")}
            className="absolute left-0 z-10 bg-gradient-to-r from-background to-transparent pr-4"
            aria-label="向左滚动"
          >
            <ChevronLeft className="size-4" />
          </Button>
        )}
        <nav
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto scrollbar-hide"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {SECTIONS.map((s) => {
            const isActive = active === s.key;
            return (
              <Button
                key={s.key}
                type="button"
                variant={isActive ? "default" : "outline"}
                size="sm"
                onClick={() => onSelect(s.key)}
                className={cn(
                  "shrink-0 rounded-full text-xs font-medium",
                  isActive
                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                    : "bg-transparent hover:bg-muted"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                {s.label}
              </Button>
            );
          })}
        </nav>
        {canScrollRight && (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => scroll("right")}
            className="absolute right-0 z-10 bg-gradient-to-l from-background to-transparent pl-4"
            aria-label="向右滚动"
          >
            <ChevronRight className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
