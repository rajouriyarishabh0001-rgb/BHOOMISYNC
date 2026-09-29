import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Eye, EyeOff, KeyRound, Layers3, LockKeyhole, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import './PasswordRecoveryPage.css';

export default function PasswordRecoveryPage({ mode = 'forgot' }: { mode?: 'forgot' | 'create' }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
    const [token, setToken] = useState(params.get('token') || '');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(''); setMessage('');
    if (mode === 'forgot' && !email.trim()) { setError('Enter your Officer ID or email.'); return; }
    if (mode === 'create' && !token.trim()) { setError('Enter the reset token from your password reset message.'); return; }
    if (mode === 'create' && password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (mode === 'create' && password !== confirmation) { setError('Passwords do not match.'); return; }
    setBusy(true);
    try {
      const result: { message: string; reset_token?: string | null } = mode === 'forgot' ? await api.forgotPassword(email.trim()) : await api.createPassword(token.trim(), password);
      setMessage(result.message);
      if (mode === 'forgot' && result.reset_token) setToken(result.reset_token);
      if (mode === 'create') window.setTimeout(() => navigate('/officer/login'), 900);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Password request failed.'); }
    finally { setBusy(false); }
  };

  return <main className="recovery-page"><div className="recovery-brand"><span><Layers3 size={18}/></span>BHOOMI<span>SYNC</span></div><section className="recovery-card"><div className="recovery-icon"><ShieldCheck size={24}/></div><div className="recovery-eyebrow">SECURE ACCOUNT ACCESS</div><h1>{mode === 'forgot' ? 'Forgot password?' : 'Create a new password'}</h1><p>{mode === 'forgot' ? 'Enter your officer email and we will help you securely reset your password.' : 'Use your secure reset token to set a new password for the Officer Dashboard.'}</p><form onSubmit={submit} noValidate>{mode === 'forgot' ? <><label htmlFor="recovery-email">Officer ID / Email</label><div className="recovery-input"><KeyRound size={16}/><input id="recovery-email" type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="officer@department.gov" autoComplete="email"/></div></> : <><label htmlFor="reset-token">Reset token</label><div className="recovery-input"><KeyRound size={16}/><input id="reset-token" value={token} onChange={event => setToken(event.target.value)} placeholder="Paste your reset token" autoComplete="one-time-code"/></div><label htmlFor="new-password">New password</label><div className="recovery-input"><LockKeyhole size={16}/><input id="new-password" type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password"/><button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div><label htmlFor="confirm-password">Confirm password</label><div className="recovery-input"><LockKeyhole size={16}/><input id="confirm-password" type={showPassword ? 'text' : 'password'} value={confirmation} onChange={event => setConfirmation(event.target.value)} placeholder="Repeat your new password" autoComplete="new-password"/></div></>}{error && <div className="recovery-error" role="alert">{error}</div>}{message && <div className="recovery-success" role="status"><CheckCircle2 size={16}/>{message}{mode === 'forgot' && token && <Link to={`/officer/create-password?token=${encodeURIComponent(token)}`}>Continue to create password <ArrowRight size={14}/></Link>}</div>}<button className="recovery-submit" disabled={busy}>{busy ? 'Processing securely...' : mode === 'forgot' ? 'Send reset instructions' : 'Create password'} <ArrowRight size={16}/></button></form><Link className="recovery-back" to="/officer/login">← Return to Officer Login</Link></section></main>;
}
