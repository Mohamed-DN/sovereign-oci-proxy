import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import { MOCK_USERS } from '../services/mockData';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [role, setRole] = useState(() => {
    return localStorage.getItem('neronet_active_role') || 'super-admin';
  });

  const [user, setUser] = useState(() => {
    return role === 'super-admin' ? MOCK_USERS[0] : MOCK_USERS[1];
  });

  const [token, setToken] = useState(() => {
    return localStorage.getItem('neronet_jwt_token') || 'mock_jwt_token_admin_sovereign';
  });

  useEffect(() => {
    localStorage.setItem('neronet_active_role', role);
    const matchedUser = role === 'super-admin' ? MOCK_USERS[0] : MOCK_USERS[1];
    setUser(matchedUser);
  }, [role]);

  const switchRole = (newRole) => {
    setRole(newRole);
  };

  const login = async (username, password) => {
    const res = await api.auth.login(username, password);
    if (res && res.user) {
      setUser(res.user);
      setRole(res.user.role);
      setToken(res.token);
      return res;
    }
    throw new Error('Authentication failed');
  };

  const logout = async () => {
    await api.auth.logout();
    setToken(null);
    setRole('user');
    setUser(MOCK_USERS[1]);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        tier: user?.tier || 'cloud_managed',
        token,
        isAuthenticated: !!token,
        switchRole,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

export default AuthContext;
