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
  const API_BASE = process.env.NEXT_PUBLIC_API_URL|| "https://api.mahisidda.com";

  useEffect(() => {
    async function fetchPopular() {
      try {
        setLoading(true);
        if (!API_BASE) {
          throw new Error("Environment variable NEXT_PUBLIC_API_URL is not defined");
        }

        const res = await fetch(`${API_BASE}/api/popular_books?limit=${limit}`);
        if (!res.ok) {
          throw new Error(`Failed to fetch: ${res.status} ${res.statusText}`);
        }

        const data: Book[] = await res.json();
        setBooks(shuffleArray(data));
      } catch (error) {
        console.error("Error fetching popular books:", error);
        setBooks([]);
      } finally {
        setLoading(false);
      }
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

  if (!loading && books.length === 0) {
    return (
      <div className="text-center text-gray-500">
        No popular books found. Please try again later.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {books.map((book) => (
        <div
          key={book.Book_ID}
          onClick={() => onToggle(book.Book_ID)}
          className={`cursor-pointer ${
            selected.includes(book.Book_ID) ? "ring-2 ring-green-500" : ""
          }`}
        >
          <BookCard book={book} />
        </div>
      ))}
    </div>
  );
}
