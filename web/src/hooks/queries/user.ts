import { useQuery } from "@tanstack/react-query";

import client from "../../lib/client";
import { type User, userSchema } from "../../models/user";

/**
 * API call to fetch the currently authenticated user's profile.
 * Validates the response against the userSchema.
 *
 * @returns A promise resolving to the validated User data.
 */
export const fetchUser = async (): Promise<User> => {
  const response = await client.get<User>("/v2/user/me");
  return userSchema.parse(response.data);
};

/**
 * Hook to retrieve the authenticated user's profile from the server.
 * Used for session management and route protection.
 * Retries are disabled to prevent endless loops on 401/403 errors.
 *
 * @returns A query object containing the User data.
 */
export const useUser = () => {
  return useQuery({
    queryKey: ["auth-user"],
    queryFn: fetchUser,
    retry: false,
  });
};
