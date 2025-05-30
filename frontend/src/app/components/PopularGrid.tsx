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
  const [error, setError] = useState<string | null>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    const fetchPopularBooks = async () => {
      console.log("Attempting to fetch popular books...");
      console.log("NEXT_PUBLIC_API_URL value is:", API_BASE);

      if (!API_BASE) {
        console.error("CRITICAL: NEXT_PUBLIC_API_URL is not available to frontend code!");
        setError("API URL is not configured.");
        setLoading(false);
        return;
      }

      const popularBooksEndpoint = `${API_BASE}/popular_books?limit=${limit}`;
      console.log("Constructed popular books endpoint:", popularBooksEndpoint);

      try {
        setLoading(true);
        const response = await fetch(popularBooksEndpoint);
        console.log("Popular books API response status:", response.status);

        if (!response.ok) {
          const errorText = await response.text();
          console.error("Error fetching popular books, status:", response.status, "Response:", errorText);
          setError(`Failed to fetch books: ${response.status}`);
          setLoading(false);
          return;
        }
        const data: Book[] = await response.json();
        console.log("Popular books data received:", data);
        setBooks(shuffleArray(data));
      } catch (err) {
        console.error("Error during fetch popular books call:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPopularBooks();
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

  if (error) {
    return (
      <div className="text-center text-red-500">
        Error loading books: {error}
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
