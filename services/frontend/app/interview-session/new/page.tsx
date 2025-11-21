"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createInterview } from "@/modules/interview/actions";

function NewInterviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const hasCreatedRef = useRef(false);

  useEffect(() => {
    // Prevent duplicate creation in React Strict Mode
    if (hasCreatedRef.current) return;

    const initializeInterview = async () => {
      try {
        // Get params from URL
        const company = searchParams.get("company") || "Free Practice";
        const role = searchParams.get("role") || "Software Engineer";
        const level = searchParams.get("level") || "Senior";
        const type = searchParams.get("type") || "system_design";

        // Mark as created before async call
        hasCreatedRef.current = true;

        // Create interview record using Server Action
        const interview = await createInterview({ company, role, level, type });

        // Redirect to the actual interview page with the real ID
        if (type === "system_design") {
          router.replace(`/interview-session/${interview.id}/system-design`);
        } else {
          router.replace(`/interview-session/${interview.id}/coding`);
        }
      } catch (err) {
        console.error("Failed to create interview:", err);
        setError(
          err instanceof Error ? err.message : "Failed to create interview",
        );
        hasCreatedRef.current = false; // Reset on error
      }
    };

    initializeInterview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Failed to Start Interview
          </h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-lg text-gray-600">Starting your interview...</p>
      </div>
    </div>
  );
}

export default function NewInterviewPage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen w-screen flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-lg text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <NewInterviewContent />
    </Suspense>
  );
}
