"use client";

const SECTIONS = [
  { key: "core_experiences", label: "Core" },
  { key: "important_experiences", label: "Important" },
  { key: "food", label: "Food" },
  { key: "lodging", label: "Lodging" },
  { key: "transport", label: "Transport" },
  { key: "budget", label: "Budget" },
  { key: "tips", label: "Tips" },
  { key: "reference_routes", label: "Routes" },
];

export default function ReportNav({ active, onSelect }: { active: string; onSelect: (key: string) => void }) {
  return (
    <nav className="flex flex-wrap gap-2 mb-6">
      {SECTIONS.map((s) => (
        <button
          key={s.key}
          onClick={() => onSelect(s.key)}
          className={`px-4 py-2 rounded-full text-sm font-medium ${
            active === s.key ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
          }`}
        >
          {s.label}
        </button>
      ))}
    </nav>
  );
}
