"use client";

import { useState } from "react";
import PopularGrid from "./components/PopularGrid";
import BookCard from "./components/BookCard";

type Rec = {
  Book_ID: string;
  Book_Title: string;
  Recommendation_Score: number;
};

export default function Home() {
  const [selected, setSelected] = useState<string[]>([]);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  const toggleSelect = (isbn: string) => {
    setSelected((prev) =>
      prev.includes(isbn) ? prev.filter((i) => i !== isbn) : [...prev, isbn]
    );
  };

  const handleSubmit = async () => {
    setError("");
    if (selected.length < 2) {
      setError("Please select at least 2 books.");
      return;
    }
    setLoading(true);
    setRecs([]);
    try {
      const res = await fetch(`${API_BASE}/recommend_by_books`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ liked_books: selected }),
      });
      if (!res.ok) throw new Error("Server error");
      const data: Rec[] = await res.json();
      setRecs(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    }
    setLoading(false);
  };

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">📚 Choose Two Books You Loved</h1>
      <p className="mb-2 text-gray-600">
        Click on at least two books below to get personalized recommendations.
      </p>

      <PopularGrid
        limit={20}
        selected={selected}
        onToggle={toggleSelect}
      />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="mt-6 px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700"
      >
        {loading ? "Thinking…" : "Get Recommendations"}
      </button>

      {error && <p className="text-red-500 mt-4">{error}</p>}

      {recs.length > 0 && (
        <section
          data-testid="recommendations-list"    {/* ← added test-id here */}
          className="mt-8"
        >
          <h2 className="text-2xl font-semibold mb-4">You Might Also Like:</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recs.map((r, i) => (
              <BookCard key={i} book={r} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
