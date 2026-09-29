import { useEffect, useState, type ReactNode } from 'react';
import { Bell, ChevronRight, Layers3, LogOut, Menu, UserRound, X } from 'lucide-react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api, OfficerProfile, officerHomePath } from '../services/api';

const navigation = [
  { label: 'Dashboard', path: 'department', permission: 'PROPERTY_VIEW' },
  { label: 'My Records', path: '/officer/records', permission: 'RECORD_VIEW' },
  { label: 'Search', path: '/officer/search', permission: 'PROPERTY_VIEW' },
  { label: 'GIS workspace', path: '/officer/gis', permission: 'GIS_VIEW' },
  { label: 'Conflicts', path: '/officer/conflicts', permission: 'CONFLICT_VIEW' },
  { label: 'Verification', path: '/officer/verification', permission: 'VERIFICATION_VIEW' },
  { label: 'Data sources', path: '/officer/data-sources', permission: 'RECORD_UPLOAD' },
  { label: 'AI matching', path: '/officer/ai-matching', permission: 'AI_VIEW' },
  { label: 'Satellite', path: '/officer/satellite', permission: 'SATELLITE_VIEW' },
  { label: 'Reports', path: '/officer/reports', permission: 'REPORT_VIEW' },
  { label: 'Notifications', path: '/officer/notifications', permission: 'RECORD_VIEW' },
  { label: 'Audit', path: '/officer/audit', permission: 'AUDIT_VIEW' },
  { label: 'Manage officers', path: '/officer/admin', permission: 'USER_MANAGE' },
];

export default function OfficerShell({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<(OfficerProfile & { is_verified: boolean }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem('bhoomisync_access_token')) { setLoading(false); return; }
    api.officerMe().then(result => setProfile(result.data)).catch(() => {
      api.officerLogout();
      navigate('/officer/login', { replace: true });
    }).finally(() => setLoading(false));
  }, [navigate]);

  if (!localStorage.getItem('bhoomisync_access_token')) return <Navigate to="/officer/login" replace/>;
  if (loading) return <div className="empty-state"><span>Verifying officer identity...</span></div>;
  if (!profile) return <Navigate to="/officer/login" replace/>;

  const departmentLabel = profile.department || 'Department';
  const initials = profile.name.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase();
  const visibleNavigation = navigation.filter(item => profile.permissions.includes(item.permission));
  const logout = () => {
    void api.officerLogout().finally(() => navigate('/officer/login', { replace: true }));
  };

  return <div className="app-shell officer-shell">
    <header className="officer-topbar">
      <button className="icon-button mobile-only" type="button" onClick={() => setOpen(value => !value)} aria-label={open ? 'Close navigation' : 'Open navigation'}>{open ? <X/> : <Menu/>}</button>
      <Link className="brand" to="/"><span className="brand-mark"><Layers3 size={18}/></span><span>BHOOMI<span>SYNC</span></span></Link>
      <div className="context"><span className="context-label">OFFICER WORKSPACE</span><span className="context-divider"/>{departmentLabel}<ChevronRight size={14}/></div>
      <div className="topbar-right"><Link className="icon-button" to="/officer/notifications" aria-label="Notifications" title="Notifications"><Bell size={17}/></Link><Link className="icon-button" to="/officer/profile" aria-label="Officer profile" title="Officer profile"><UserRound size={17}/></Link><button className="icon-button" type="button" onClick={logout} aria-label="Log out" title="Log out"><LogOut size={17}/></button><div className="avatar">{initials}</div></div>
    </header>
    <aside className={open ? 'sidebar officer-sidebar open' : 'sidebar officer-sidebar'}>
      <div className="sidebar-kicker">INTELLIGENCE CONSOLE</div>
      <nav>{visibleNavigation.map(item => { const path = item.path === 'department' ? officerHomePath(profile.department_key) : item.path; return <Link key={item.label} to={path} onClick={() => setOpen(false)} className={location.pathname === path ? 'active' : ''}>{item.label}<ChevronRight size={14}/></Link>; })}</nav>
      <div className="role-card"><div className="avatar small">{initials}</div><div><strong>{profile.name}</strong><span>{profile.designation}</span><span>{departmentLabel}</span><span>{profile.officer_id}</span><span>{profile.email}</span><span>{profile.is_verified ? 'Verified officer' : 'Verification pending'}</span></div></div>
      <Link className="back-citizen" to="/user"><ChevronRight size={14}/> View citizen portal</Link>
    </aside>
    <main className="content-area officer-content">{children}</main>
  </div>;
}
