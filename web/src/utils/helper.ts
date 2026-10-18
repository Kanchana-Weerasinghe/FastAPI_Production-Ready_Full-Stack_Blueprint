import { apiBaseUrl } from "../lib/config";

/**
 * Extracts a human-readable error message from an unknown error object.
 *
 * @param error - The error object or string to parse.
 * @returns The extracted message or undefined.
 */
export const getErrorMessage = (error: unknown): string | undefined => {
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) {
    return (error as { message: string }).message;
  }
  return undefined;
};

/**
 * Formats a byte count into a human-readable string (e.g., "1.2 MB").
 *
 * @param bytes - The number of bytes to format.
 * @returns A formatted string with the appropriate unit.
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

/**
 * Maximum allowed file size for uploads (50MB).
 */
export const MAX_FILE_SIZE = 50 * 1024 * 1024;

/**
 * Validates if a file's size is within the allowed limit.
 *
 * @param file - The File object to check.
 * @returns True if valid, false otherwise.
 */
export const validateFileSize = (file: File): boolean => {
  return file.size <= MAX_FILE_SIZE;
};

/**
 * Formats an ISO date string or Date object into the application's standard format:
 * "Month Day Year, Hour:Minute AM/PM" (e.g., "May 10 2024, 2:30 PM").
 *
 * @param dateString - The date to format.
 * @returns A formatted date string.
 */
export const formatDate = (dateString: string | Date): string => {
  const date = new Date(dateString);
  const month = date.toLocaleString("en-US", { month: "long" });
  const day = date.getDate();
  const year = date.getFullYear();
  const hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 || 12;

  return `${month} ${day} ${year}, ${displayHours}:${minutes} ${ampm}`;
};

/**
 * Generates the full backend download URL for a specific attachment.
 *
 * @param fileId - The unique identifier of the file.
 * @returns The absolute URL for downloading the file.
 */
export const getDownloadUrl = (fileId: string): string => {
  return `${apiBaseUrl()}/v2/attachments/${fileId}:download`;
};
