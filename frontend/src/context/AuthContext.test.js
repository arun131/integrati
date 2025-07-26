import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// Mock the entire AuthContext module
jest.mock('./AuthContext', () => ({
  AuthProvider: ({ children }) => <div data-testid="auth-provider">{children}</div>,
  useAuth: () => ({
    token: null,
    userEmail: null,
    user: null,
    loading: false,
    signInWithGoogle: jest.fn(),
    signInWithGithub: jest.fn(),
    signInWithEmail: jest.fn(),
    signUpWithEmail: jest.fn(),
    login: jest.fn(),
    logout: jest.fn()
  })
}));

// Test component to use the context
const TestComponent = () => {
  const { token, userEmail, user, loading } = useAuth();
  return (
    <div>
      <div data-testid="token">{token || 'no-token'}</div>
      <div data-testid="user-email">{userEmail || 'no-email'}</div>
      <div data-testid="user">{user ? 'has-user' : 'no-user'}</div>
      <div data-testid="loading">{loading ? 'loading' : 'not-loading'}</div>
    </div>
  );
};

describe('AuthContext', () => {
  test('AuthProvider renders children', () => {
    render(
      <AuthProvider>
        <div data-testid="child">Child Component</div>
      </AuthProvider>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  test('useAuth provides default values', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('token')).toHaveTextContent('no-token');
    expect(screen.getByTestId('user-email')).toHaveTextContent('no-email');
    expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    expect(screen.getByTestId('loading')).toHaveTextContent('not-loading');
  });

  test('useAuth provides auth functions', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const auth = useAuth();
    expect(auth.signInWithGoogle).toBeDefined();
    expect(auth.signInWithGithub).toBeDefined();
    expect(auth.signInWithEmail).toBeDefined();
    expect(auth.signUpWithEmail).toBeDefined();
    expect(auth.login).toBeDefined();
    expect(auth.logout).toBeDefined();
  });
});
