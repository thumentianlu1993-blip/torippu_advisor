"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MapPin, Calendar, Users, Sparkles, Banknote, AlertCircle } from "lucide-react";

const BUDGET_LEVELS = [
  { value: "budget", label: "经济" },
  { value: "mid-range", label: "舒适" },
  { value: "luxury", label: "豪华" },
];

type FormState = {
  destination: string;
  duration_days: string;
  travel_time: string;
  departure: string;
  traveler_structure: string;
  preferences: string;
  budget_level: string;
  constraints: string;
};

const INITIAL_FORM: FormState = {
  destination: "",
  duration_days: "",
  travel_time: "",
  departure: "",
  traveler_structure: "",
  preferences: "",
  budget_level: "",
  constraints: "",
};

function FieldGroup({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Icon className="size-4" />
        </div>
        <h3 className="font-heading text-base font-semibold">{title}</h3>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </div>
  );
}

export default function ProjectForm({ onCreated }: { onCreated?: (project: any) => void }) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setTouched((prev) => ({ ...prev, [field]: true }));
    setError("");
  };

  const validate = useMemo(() => {
    const errors: Partial<Record<keyof FormState, string>> = {};
    if (!form.destination.trim()) errors.destination = "请填写目的地";
    const days = parseInt(form.duration_days, 10);
    if (!form.duration_days || Number.isNaN(days) || days < 1 || days > 60) {
      errors.duration_days = "行程天数需在 1 到 60 天之间";
    }
    if (!form.departure.trim()) errors.departure = "请填写出发地";
    return errors;
  }, [form]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({
      destination: true,
      duration_days: true,
      departure: true,
    });

    if (Object.keys(validate).length > 0) {
      setError("请修正标红的字段。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const project = await api.createProject({
        ...form,
        duration_days: parseInt(form.duration_days, 10),
      });
      onCreated?.(project);
    } catch (err: any) {
      setError(err.message || "创建失败，请重试。");
    } finally {
      setLoading(false);
    }
  };

  const fieldError = (field: keyof FormState) =>
    touched[field] && validate[field] ? validate[field] : undefined;

  return (
    <Card className="editorial-shadow">
      <CardHeader>
        <CardTitle className="text-xl sm:text-2xl">规划你的行程</CardTitle>
        <CardDescription>
          告诉我们你想去哪里，我们会生成一份可分享的旅行报告。
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-8">
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <FieldGroup icon={MapPin} title="目的地">
            <div className="sm:col-span-2">
              <Label htmlFor="destination">目的地 *</Label>
              <Input
                id="destination"
                name="destination"
                value={form.destination}
                onChange={(e) => handleChange("destination", e.target.value)}
                placeholder="例如：日本京都"
                aria-invalid={!!fieldError("destination")}
              />
              {fieldError("destination") && (
                <p className="mt-1 text-xs text-destructive">{fieldError("destination")}</p>
              )}
            </div>
            <div>
              <Label htmlFor="departure">出发地 *</Label>
              <Input
                id="departure"
                name="departure"
                value={form.departure}
                onChange={(e) => handleChange("departure", e.target.value)}
                placeholder="例如：上海"
                aria-invalid={!!fieldError("departure")}
              />
              {fieldError("departure") && (
                <p className="mt-1 text-xs text-destructive">{fieldError("departure")}</p>
              )}
            </div>
            <div>
              <Label htmlFor="travel_time">出行日期</Label>
              <Input
                id="travel_time"
                name="travel_time"
                value={form.travel_time}
                onChange={(e) => handleChange("travel_time", e.target.value)}
                placeholder="例如：2026-11-01 至 2026-11-07"
              />
            </div>
          </FieldGroup>

          <FieldGroup icon={Calendar} title="时间">
            <div>
              <Label htmlFor="duration_days">行程天数 *</Label>
              <Input
                id="duration_days"
                name="duration_days"
                type="number"
                min={1}
                max={60}
                value={form.duration_days}
                onChange={(e) => handleChange("duration_days", e.target.value)}
                placeholder="7"
                aria-invalid={!!fieldError("duration_days")}
              />
              {fieldError("duration_days") && (
                <p className="mt-1 text-xs text-destructive">{fieldError("duration_days")}</p>
              )}
            </div>
          </FieldGroup>

          <FieldGroup icon={Users} title="同行人">
            <div className="sm:col-span-2">
              <Label htmlFor="traveler_structure">旅伴</Label>
              <Input
                id="traveler_structure"
                name="traveler_structure"
                value={form.traveler_structure}
                onChange={(e) => handleChange("traveler_structure", e.target.value)}
                placeholder="例如：2 位成人，1 位儿童"
              />
            </div>
          </FieldGroup>

          <FieldGroup icon={Sparkles} title="偏好">
            <div className="sm:col-span-2">
              <Label htmlFor="preferences">你最期待什么？</Label>
              <Textarea
                id="preferences"
                name="preferences"
                value={form.preferences}
                onChange={(e) => handleChange("preferences", e.target.value)}
                placeholder="寺庙、美食、红叶、徒步……"
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="budget_level">预算等级</Label>
              <Select value={form.budget_level} onValueChange={(value) => handleChange("budget_level", value || "")}>
                <SelectTrigger id="budget_level" className="w-full">
                  <SelectValue placeholder="选择预算…" />
                </SelectTrigger>
                <SelectContent>
                  {BUDGET_LEVELS.map((level) => (
                    <SelectItem key={level.value} value={level.value}>
                      {level.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="constraints">限制条件</Label>
              <Input
                id="constraints"
                name="constraints"
                value={form.constraints}
                onChange={(e) => handleChange("constraints", e.target.value)}
                placeholder="例如：不吃生食、避免长时间徒步"
              />
            </div>
          </FieldGroup>
        </CardContent>
        <CardFooter className="flex-col gap-3">
          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {loading ? "正在创建行程…" : "创建行程方案"}
          </Button>
          <p className="text-xs text-muted-foreground">
            创建即表示同意把报告分享给任何拥有链接的人。
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
