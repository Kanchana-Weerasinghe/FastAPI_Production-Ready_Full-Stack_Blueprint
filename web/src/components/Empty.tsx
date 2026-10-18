interface EmptyStateProps {
  isLoading?: boolean;
  message?: string;
  subMessage?: string;
}

/**
 * A fallback UI component used when a list is empty or data is loading.
 * Provides a skeleton loader and customizable messaging.
 *
 * @param isLoading - If true, shows a spinner instead of the empty message.
 * @param message - Main heading text. Defaults to "No items found.".
 * @param subMessage - Secondary supporting text.
 */
export function EmptyState({
  isLoading,
  message = "No items found.",
  subMessage,
}: EmptyStateProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-400"></div>
      </div>
    );
  }

  return (
    <div className="bg-white/50 border-2 border-dashed border-brand-200 rounded-2xl p-12 text-center">
      <p className="text-brand-300 font-bold">{message}</p>
      {subMessage && (
        <p className="text-brand-300/60 text-sm mt-1">{subMessage}</p>
      )}
    </div>
  );
}
