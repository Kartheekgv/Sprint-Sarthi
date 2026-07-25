import { useCallback } from 'react';
import { useLocalStorage } from './useLocalStorage';

export interface AuthUser {
  username: string;
  name: string;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
}

// Dummy credentials for development
const VALID_CREDENTIALS = {
  username: 'admin',
  password: 'password',
};

const DUMMY_USER: AuthUser = {
  username: 'admin',
  name: 'Admin User',
};

export function useAuth() {
  const [authState, setAuthState] = useLocalStorage<AuthState>('sprint-sarthi-auth', {
    user: null,
    isAuthenticated: false,
  });

  const login = useCallback(
    (username: string, password: string): { success: boolean; error?: string } => {
      if (username === VALID_CREDENTIALS.username && password === VALID_CREDENTIALS.password) {
        setAuthState({
          user: DUMMY_USER,
          isAuthenticated: true,
        });
        return { success: true };
      }
      return { success: false, error: 'Invalid username or password' };
    },
    [setAuthState]
  );

  const validateCredentials = useCallback(
    (username: string, password: string): { success: boolean; error?: string } => {
      if (username === VALID_CREDENTIALS.username && password === VALID_CREDENTIALS.password) {
        return { success: true };
      }
      return { success: false, error: 'Invalid username or password' };
    },
    []
  );

  const logout = useCallback(() => {
    setAuthState({
      user: null,
      isAuthenticated: false,
    });
  }, [setAuthState]);

  return {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    login,
    logout,
    validateCredentials,
  };
}
