export default function SkeletonCard() {
    return (
      <div className="animate-pulse p-4 border rounded shadow-sm bg-white">
        <div className="w-full h-40 bg-gray-300 mb-3 rounded"></div>
        <div className="h-5 bg-gray-300 rounded mb-2 w-3/4"></div>
        <div className="h-4 bg-gray-300 rounded mb-3 w-1/2"></div>
        <div className="h-3 bg-gray-300 rounded w-1/3"></div>
      </div>
    );
  }
  