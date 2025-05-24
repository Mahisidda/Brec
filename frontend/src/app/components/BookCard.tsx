"use client";

type Props = {
  book: {
    Book_ID: string;
    Book_Title: string;
    Recommendation_Score?: number;
  };
};

export default function BookCard({ book }: Props) {
  const coverUrl = `https://covers.openlibrary.org/b/isbn/${book.Book_ID}-M.jpg`;

  return (
    <div className="p-4 border rounded shadow-sm bg-white" data-testid="book-card">
      {/* 1. Book Cover */}
      <img
        src={coverUrl}
        alt={book.Book_Title}
        className="w-full h-40 object-cover mb-2"
        onError={(e) => {
          // fallback if no cover exists
          (e.currentTarget as HTMLImageElement).src = "/fallback-cover.png";
        }}
      />

      {/* 2. Title */}
      <h3 className="text-lg text-black font-semibold">{book.Book_Title}</h3>

      {/* 3. (Optional) Score */}
      {book.Recommendation_Score !== undefined && (
        <p className="text-sm text-gray-700 mt-1">
          Score: {book.Recommendation_Score.toFixed(2)}
        </p>
      )}
    </div>
  );
}
