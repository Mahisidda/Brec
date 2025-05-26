"use client";

import { useState, useEffect } from "react";
import BookCard from "./BookCard";
import Skeletoncard from "./Skeletoncard";

type Book = { Book_ID: string; Book_Title: string };
type Props = {
  limit?: number;
  selected: string[];
  onToggle: (isbn: string) => void;
};

function shuffleArray<T>(arr: T[]): T[] {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export default function PopularGrid({ limit = 20, selected, onToggle }: Props) {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    async function fetchPopular() {
      setLoading(true);
      const res = await fetch(`${API_BASE}/popular_books?limit=${limit}`);
      const data: Book[] = await res.json();
      setBooks(shuffleArray(data));  // ← shuffle here
      setLoading(false);
    }
    fetchPopular();
  }, [limit, API_BASE]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: limit }).map((_, i) => (
          <Skeletoncard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {books.map((book) => (
        <div
          key={book.Book_ID}
          onClick={() => onToggle(book.Book_ID)}
          className={`cursor-pointer ${selected.includes(book.Book_ID) ? "ring-2 ring-green-500" : ""}`}
        >
          <BookCard book={book} />
        </div>
      ))}
    </div>
  );
}
