import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, Eye, EyeOff, KeyRound, Layers3, LockKeyhole, Map, Satellite, ShieldCheck } from 'lucide-react';
import { api, officerHomePath } from '../services/api';
import './OfficerLoginPage.css';
import LanguageSelector from '../components/LanguageSelector';

export default function OfficerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState(import.meta.env.VITE_OFFICER_LOGIN_EMAIL || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    if (localStorage.getItem('bhoomisync_access_token')) {
      api.officerMe().then(result => navigate(officerHomePath(result.data.department_key), { replace: true }))
        .catch(() => { void api.officerLogout().finally(() => setCheckingSession(false)); });
    }
  }, [navigate]);

  if (localStorage.getItem('bhoomisync_access_token') && checkingSession) return <main className="officer-login-page"><div role="status">Checking authenticated officer...</div></main>;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (!email.trim()) { setError('Enter your Officer ID or email.'); return; }
    if (!password) { setError('Enter your password.'); return; }
    setBusy(true);
    try {
      await api.officerLogin({ email: email.trim(), password });
      const profile = await api.officerMe();
      setSuccess(true);
      window.setTimeout(() => navigate(officerHomePath(profile.data.department_key), { replace: true }), 450);
    } catch {
      setError('Invalid Officer ID or password.');
    } finally {
      setBusy(false);
    }
  };

  return <main className="officer-login-page">
    <section className="officer-login-visual" aria-label="GIS and satellite intelligence">
      <Link className="officer-login-brand" to="/"><span className="officer-brand-mark"><Layers3 size={19}/></span><span>BHOOMI<span>SYNC</span></span></Link>
      <div className="gis-grid" aria-hidden="true"><span className="gis-line one"/><span className="gis-line two"/><span className="gis-pin pin-one"/><span className="gis-pin pin-two"/></div>
      <div className="officer-visual-copy"><span className="officer-eyebrow"><Satellite size={14}/> SECURE OPERATIONS</span><h1>Smart GIS &amp;<br/><em>Satellite Intelligence</em></h1><p>Secure access for authorized officers to monitor, verify and manage geospatial information.</p><div className="officer-capabilities"><span><Map size={15}/> GIS layers</span><span><Satellite size={15}/> Imagery</span><span><ShieldCheck size={15}/> Verified access</span></div></div>
    </section>
    <section className="officer-login-side"><div className="officer-login-card"><div className="login-language"><LanguageSelector/></div>
      <div className="security-icon"><ShieldCheck size={24}/></div><span className="officer-eyebrow dark">OFFICER ACCESS</span><h2>Officer Login</h2><p className="officer-login-subtitle">Sign in to access the Officer Dashboard</p>
      <form onSubmit={submit} noValidate>
        <label htmlFor="officer-email">Officer ID / Email</label><div className="officer-input-wrap"><KeyRound size={17}/><input id="officer-email" type="text" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} placeholder="Enter Officer ID or email" aria-describedby={error ? 'officer-login-error' : undefined}/></div>
          <div className="officer-password-label"><label htmlFor="officer-password">Password</label><a href="/officer/login?view=forgot">Forgot Password?</a></div><div className="officer-input-wrap"><LockKeyhole size={17}/><input id="officer-password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password"/><button type="button" className="password-toggle" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div>
        <label className="remember-control"><input type="checkbox" checked={rememberMe} onChange={event => setRememberMe(event.target.checked)}/><span>Remember me on this device</span></label>
        {error && <div className="officer-login-error" id="officer-login-error" role="alert">{error}</div>}{success && <div className="officer-login-success" role="status"><ShieldCheck size={16}/> Authentication successful. Opening dashboard...</div>}
        <button className="officer-signin" type="submit" disabled={busy || success}>{busy ? <><Activity size={17} className="spin"/> Signing in securely</> : <>Sign In <ArrowRight size={17}/></>}</button>
      </form><div className="officer-login-footer"><span><LockKeyhole size={13}/> Encrypted officer session</span><span>Need access? Contact your administrator.</span></div>
    </div></section>
  </main>;
}
