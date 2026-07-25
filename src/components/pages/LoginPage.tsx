import { useState, useEffect, type FormEvent } from 'react';
import { IconEye, IconEyeOff, IconLogin, IconWarning } from '../icons';
import { Logo } from '../common/Logo';
import { Button } from '../common/Button';

interface LoginPageProps {
  onLogin: (username: string, password: string) => { success: boolean; error?: string };
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Scroll to middle of page on mount
  useEffect(() => {
    const scrollToMiddle = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo(0, scrollHeight / 2);
    };
    scrollToMiddle();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500));

    const result = onLogin(username, password);
    if (!result.success) {
      setError(result.error || 'Login failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <Logo />
          <h1 className="login-title">Welcome back</h1>
          <p className="login-subtitle">Sign in to Sprint Sarthi AI Assistant</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error">
              <IconWarning size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="login-field">
            <label htmlFor="username" className="login-label">
              Username
            </label>
            <input
              id="username"
              type="text"
              className="login-input"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="password" className="login-label">
              Password
            </label>
            <div className="login-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="login-input login-input--password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="login-toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            icon={<IconLogin size={18} />}
            disabled={isLoading || !username || !password}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>

        <div className="login-footer">
          <p className="login-hint">
            <strong>Demo credentials:</strong> admin / password
          </p>
        </div>
      </div>

      <div className="login-background">
        <iframe 
          src="/globe-animation.html" 
          className="login-bg-globe"
          title="Animated globe background"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
