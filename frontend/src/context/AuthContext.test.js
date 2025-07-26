import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// Mock Firebase auth
jest.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
  githubProvider: {}
}));

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn()
}));

// Mock fetch
global.fetch = jest.fn();

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
  beforeEach(() => {
    // Clear localStorage
    localStorage.clear();
    // Reset fetch mock
    fetch.mockClear();
  });

  test('AuthProvider renders children when not loading', () => {
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
  });

  test('useAuth throws error when used outside provider', () => {
    // Suppress console.error for this test
    const originalError = console.error;
    console.error = jest.fn();

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within an AuthProvider');

    console.error = originalError;
  });
});
