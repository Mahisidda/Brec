export default function SkeletonCard() {
    return (
      <div className="animate-pulse p-4 border rounded shadow-sm bg-white">
        <div className="w-full h-40 bg-gray-200 mb-2 rounded"></div>
        <div className="h-4 bg-gray-200 rounded mb-1"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }
  