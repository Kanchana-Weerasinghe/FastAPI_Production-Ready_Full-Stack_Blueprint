import axios from "axios";

/**
 * RFC 9457 Problem Details returned by the API for every error.
 * Branch on `code` (stable contract), show `detail` to users.
 */
export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  instance?: string;
  request_id?: string;
  errors?: { field: string; message: string; type: string }[];
  [extension: string]: unknown;
}

/** Extracts the Problem Details body from an Axios error, if the API sent one. */
export const getProblem = (error: unknown): Problem | undefined => {
  if (!axios.isAxiosError(error)) return undefined;
  const data = error.response?.data as Partial<Problem> | undefined;
  return data && typeof data.code === "string" ? (data as Problem) : undefined;
};

/** A user-facing message for an API error, falling back when the response isn't a problem document. */
export const problemMessage = (error: unknown, fallback: string): string =>
  getProblem(error)?.detail ?? fallback;
