import { Store } from "@tanstack/react-store";

import type { User } from "../models/user";

export interface AuthState {
  user: User | null;
}

/**
 * Global authentication store using TanStack Store.
 * Keeps track of the currently logged-in user profile.
 */
export const authStore = new Store<AuthState>({
  user: null,
});

/**
 * Selector to check if a user is currently logged in.
 */
export const selectIsAuthenticated = (state: AuthState) => !!state.user;

/**
 * Updates the store with new user data.
 * @param user - The User profile object.
 */
export const setAuth = (user: User) => {
  authStore.setState((state) => ({
    ...state,
    user,
  }));
};

/**
 * Clears the user data from the store, effectively logging them out locally.
 */
export const clearAuth = () => {
  authStore.setState((state) => ({
    ...state,
    user: null,
  }));
};
