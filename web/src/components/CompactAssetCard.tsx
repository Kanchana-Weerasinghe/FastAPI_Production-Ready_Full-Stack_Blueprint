import { Download, Trash2 } from "lucide-react";

interface CompactAssetCardProps {
  name: string;
  type: string;
  size: string;
  date: string;
  iconUrl: string;
  onDownload?: () => void;
  onDelete?: () => void;
  readOnly?: boolean;
}

/**
 * A condensed version of the AssetCard, optimized for list views.
 * Supports a read-only mode to disable hover effects and interactive actions.
 *
 * @param name - The filename.
 * @param type - The file type/extension.
 * @param size - Formatted file size.
 * @param date - Upload date.
 * @param iconUrl - URL to the file icon.
 * @param onDownload - Callback for file download.
 * @param onDelete - Optional callback for file deletion.
 * @param readOnly - If true, disables interaction and hover effects.
 */
export function CompactAssetCard({
  name,
  type,
  size,
  date,
  iconUrl,
  onDownload,
  onDelete,
  readOnly = false,
}: CompactAssetCardProps) {
  return (
    <div
      className={`bg-white border-2 border-brand-200/50 rounded-xl px-4 py-2.5 transition-all group flex items-center gap-4 ${
        readOnly ? "cursor-default" : "hover:border-brand-400 cursor-pointer"
      }`}
    >
      <div
        className={`shrink-0 transition-transform ${
          !readOnly && "group-hover:scale-110"
        }`}
      >
        <img src={iconUrl} alt={type} className="w-10 h-10 object-contain" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-bold text-brand-600 truncate">{name}</h3>
        <div className="flex items-center gap-3 text-xs font-bold text-brand-300/60 uppercase tracking-wider">
          <span>{size}</span>
          <span className="font-mono">{date}</span>
        </div>
      </div>
      <div className="flex gap-1 transition-all">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDownload?.();
          }}
          className="p-1.5 text-brand-300 hover:text-brand-400 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
          title="Download"
        >
          <Download size={16} />
        </button>
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
            className="p-1.5 text-brand-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
            title="Delete"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
