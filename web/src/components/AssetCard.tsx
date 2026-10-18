import { Download, Trash2 } from "lucide-react";

interface AssetCardProps {
  name: string;
  type: string;
  size: string;
  date: string;
  iconUrl: string;
  onDownload?: () => void;
  onDelete?: () => void;
}

/**
 * A card component for displaying file assets.
 * Displays file metadata (name, size, date) and provides download/delete actions.
 *
 * @param name - The original filename.
 * @param type - The file mime type or extension.
 * @param size - Formatted file size string.
 * @param date - Formatted upload date.
 * @param iconUrl - URL to the file type icon.
 * @param onDownload - Optional callback for file download.
 * @param onDelete - Optional callback for file deletion.
 */
export function AssetCard({
  name,
  type,
  size,
  date,
  iconUrl,
  onDownload,
  onDelete,
}: AssetCardProps) {
  return (
    <div className="bg-white border-2 border-brand-200/50 rounded-xl p-4 hover:border-brand-400 transition-all group cursor-pointer">
      <div className="flex items-start justify-between mb-4">
        <div className="p-1 group-hover:scale-110 transition-transform">
          <img
            src={iconUrl}
            alt={type}
            className="w-10 h-10 object-contain opacity-80"
          />
        </div>
        <div className="flex gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDownload?.();
            }}
            className="p-2 text-brand-300 hover:text-brand-400 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
            title="Download"
          >
            <Download size={18} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
            className="p-2 text-brand-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
            title="Delete"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
      <div>
        <h3 className="text-base font-bold text-gray-700 mb-1.5 truncate">
          {name}
        </h3>
        <div className="flex items-center justify-between text-xs font-bold text-brand-300/60 uppercase tracking-wider">
          <span>{size}</span>
          <span className="font-mono">{date}</span>
        </div>
      </div>
    </div>
  );
}
