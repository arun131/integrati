import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

// Mock the AuthContext to avoid Firebase dependencies in tests
jest.mock('./context/AuthContext', () => ({
  AuthProvider: ({ children }) => <div data-testid="auth-provider">{children}</div>,
  useAuth: () => ({
    user: null,
    token: null,
    loading: false
  })
}));

// Mock react-router-dom to avoid navigation issues in tests
jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }) => <div data-testid="router">{children}</div>,
  Routes: ({ children }) => <div data-testid="routes">{children}</div>,
  Route: ({ element }) => <div data-testid="route">{element}</div>,
  Navigate: () => <div data-testid="navigate">Navigate</div>,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ search: '' })
}));

describe('App Component', () => {
  test('renders without crashing', () => {
    render(<App />);
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
    expect(screen.getByTestId('router')).toBeInTheDocument();
  });

  test('renders with proper structure', () => {
    render(<App />);
    expect(screen.getByTestId('routes')).toBeInTheDocument();
  });
});
