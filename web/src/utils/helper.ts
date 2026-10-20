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
