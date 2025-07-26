import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import LoginPage from './LoginPage';

// Mock the AuthContext
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    signInWithGoogle: jest.fn(),
    signInWithGithub: jest.fn(),
    signInWithEmail: jest.fn(),
    signUpWithEmail: jest.fn(),
    login: jest.fn()
  })
}));

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  useLocation: () => ({
    search: ''
  })
}));

// Mock jwt-decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn()
}));

describe('LoginPage', () => {
  test('renders login form', () => {
    render(<LoginPage />);

    expect(screen.getByText('Welcome to Integrati')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  test('renders Google sign-in button', () => {
    render(<LoginPage />);

    expect(screen.getByText('Continue with Google')).toBeInTheDocument();
  });

  test('renders GitHub sign-in button', () => {
    render(<LoginPage />);

    expect(screen.getByText('Continue with GitHub')).toBeInTheDocument();
  });

  test('toggles between sign in and sign up', () => {
    render(<LoginPage />);

    // Initially shows "Sign In"
    expect(screen.getByText('Sign In')).toBeInTheDocument();
    expect(screen.getByText("Don't have an account? Sign Up")).toBeInTheDocument();

    // Click to toggle to sign up
    fireEvent.click(screen.getByText("Don't have an account? Sign Up"));

    // Now shows "Sign Up"
    expect(screen.getByText('Sign Up')).toBeInTheDocument();
    expect(screen.getByText('Already have an account? Sign In')).toBeInTheDocument();
  });

  test('form inputs work correctly', () => {
    render(<LoginPage />);

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(emailInput.value).toBe('test@example.com');
    expect(passwordInput.value).toBe('password123');
  });
});
