"use client";

export default function Error({ error }: { error: Error }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-red-50">
      <div className="p-6 bg-white rounded-lg shadow-lg max-w-md">
        <h1 className="text-2xl font-bold text-red-600 mb-4">
          Something went wrong
        </h1>
        <p className="text-gray-700 mb-4">{error.message || "An unexpected error occurred"}</p>
        <button
          onClick={() => window.location.href = "/"}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Go Home
        </button>
      </div>
    </div>
  );
}
