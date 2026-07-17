"use client";

import { useState } from "react";
import ProjectForm from "./components/ProjectForm";

export default function HomePage() {
  const [project, setProject] = useState<any | null>(null);

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">Travel Planner</h1>
        <ProjectForm onCreated={setProject} />

        {project && (
          <div className="mt-8 p-4 bg-green-50 border border-green-200 rounded">
            <p className="font-medium">Project created! 🎉</p>
            <p className="text-sm text-gray-700 mt-1">
              Share link:{" "}
              <a
                href={`/p/${project.token}`}
                className="text-blue-600 underline break-all"
              >
                {typeof window !== "undefined" ? `${window.location.origin}/p/${project.token}` : `#`}
              </a>
            </p>
            <a
              href={`/p/${project.token}`}
              className="inline-block mt-3 text-blue-600 underline"
            >
              View report →
            </a>
          </div>
        )}
      </div>
    </main>
  );
}
