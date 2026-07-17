"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function ProjectForm({ onCreated }: { onCreated?: (project: any) => void }) {
  const [form, setForm] = useState({
    destination: "",
    duration_days: "",
    travel_time: "",
    departure: "",
    traveler_structure: "",
    preferences: "",
    budget_level: "",
    constraints: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const project = await api.createProject({
        ...form,
        duration_days: parseInt(form.duration_days, 10),
      });
      onCreated?.(project);
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-xl mx-auto">
      {error && <p className="text-red-600">{error}</p>}
      <div>
        <label className="block text-sm font-medium">Destination *</label>
        <input
          name="destination"
          value={form.destination}
          onChange={handleChange}
          required
          className="w-full border rounded px-3 py-2"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium">Duration (days) *</label>
          <input
            name="duration_days"
            type="number"
            min={1}
            max={60}
            value={form.duration_days}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Travel time</label>
          <input
            name="travel_time"
            value={form.travel_time}
            onChange={handleChange}
            placeholder="e.g. 2026-11-01"
            className="w-full border rounded px-3 py-2"
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium">Departure *</label>
        <input
          name="departure"
          value={form.departure}
          onChange={handleChange}
          required
          className="w-full border rounded px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Travelers</label>
        <input
          name="traveler_structure"
          value={form.traveler_structure}
          onChange={handleChange}
          placeholder="e.g. 2 adults"
          className="w-full border rounded px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Preferences</label>
        <textarea
          name="preferences"
          value={form.preferences}
          onChange={handleChange}
          placeholder="e.g. temples, food, autumn leaves"
          className="w-full border rounded px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Budget level</label>
        <select
          name="budget_level"
          value={form.budget_level}
          onChange={handleChange}
          className="w-full border rounded px-3 py-2"
        >
          <option value="">Select...</option>
          <option value="budget">Budget</option>
          <option value="mid-range">Mid-range</option>
          <option value="luxury">Luxury</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Constraints</label>
        <textarea
          name="constraints"
          value={form.constraints}
          onChange={handleChange}
          placeholder="e.g. no raw food, avoid long hikes"
          className="w-full border rounded px-3 py-2"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create Travel Plan"}
      </button>
    </form>
  );
}
