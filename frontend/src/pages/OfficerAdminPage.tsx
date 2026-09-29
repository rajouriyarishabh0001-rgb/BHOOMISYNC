import { FormEvent, useEffect, useState } from 'react';
import { Activity, UserPlus } from 'lucide-react';
import { api } from '../services/api';
import './OfficerAdminPage.css';

type OfficerRow = Awaited<ReturnType<typeof api.officerAdminOfficers>>['data'][number];
type AssignmentRow = Awaited<ReturnType<typeof api.officerAdminAssignments>>['data'][number];

export default function OfficerAdminPage() {
  const [officers, setOfficers] = useState<OfficerRow[]>([]);
  const [assignments, setAssignments] = useState<AssignmentRow[]>([]);
  const [stats, setStats] = useState<{ department: string; officers: number; active_assignments: number }>();
  const [activity, setActivity] = useState<Array<{ officer_id?: string; action: string; record_id: string; reason?: string; created_at: string }>>([]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [designation, setDesignation] = useState('');
  const [targetOfficer, setTargetOfficer] = useState('');
  const [previousOfficer, setPreviousOfficer] = useState('');
  const [propertyId, setPropertyId] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const [officerResult, assignmentResult, statsResult, activityResult] = await Promise.all([api.officerAdminOfficers(), api.officerAdminAssignments(), api.officerAdminStats(), api.officerAdminActivity()]);
      setOfficers(officerResult.data);
      setAssignments(assignmentResult.data);
      setStats(statsResult.data);
      setActivity(activityResult.data);
      setTargetOfficer(current => current || officerResult.data.find(item => item.role !== 'DEPARTMENT_ADMIN')?.officer_id || '');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Department administration is unavailable.');
    } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);

  const createOfficer = async (event: FormEvent) => {
    event.preventDefault();
    setMessage('');
    try {
      await api.officerAdminCreate({ name, email, password, designation });
      setName(''); setEmail(''); setPassword(''); setDesignation('');
      setMessage('Officer account created.');
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Officer could not be created.'); }
  };
  const assignProperty = async (event: FormEvent) => {
    event.preventDefault();
    setMessage('');
    try {
      await api.officerAdminAssign({ officer_id: targetOfficer, property_id: propertyId, ...(previousOfficer ? { from_officer_id: previousOfficer } : {}) });
      setPropertyId('');
      setPreviousOfficer('');
      setMessage('Property assignment saved.');
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Assignment could not be saved.'); }
  };
  const toggleActive = async (officer: OfficerRow) => {
    try { await api.officerAdminSetActive(officer.officer_id, !officer.is_active); await refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Officer status could not be updated.'); }
  };

  return <main className="officer-admin-page">
    <header className="officer-admin-heading"><div><span>DEPARTMENT ADMINISTRATION</span><h1>Officer and record assignments</h1><p>{stats?.department || 'Department'} · department-scoped controls</p></div></header>
    {message && <div className="officer-admin-message" role="status">{message}</div>}
    <section className="officer-admin-stats"><div><span>Department officers</span><strong>{stats?.officers ?? '—'}</strong></div><div><span>Active assignments</span><strong>{stats?.active_assignments ?? '—'}</strong></div><div><span>Records available</span><strong>{assignments.length}</strong></div></section>
    <div className="officer-admin-grid">
      <form className="officer-admin-form" onSubmit={createOfficer}><h2><UserPlus size={17}/> Create officer</h2><label>Full name<input required minLength={2} value={name} onChange={event => setName(event.target.value)}/></label><label>Email<input required type="email" value={email} onChange={event => setEmail(event.target.value)}/></label><label>Designation<input value={designation} onChange={event => setDesignation(event.target.value)}/></label><label>Temporary password<input required minLength={10} type="password" value={password} onChange={event => setPassword(event.target.value)}/></label><button type="submit" disabled={!name || !email || password.length < 10}>Create account</button></form>
      <form className="officer-admin-form" onSubmit={assignProperty}><h2>Assign or reassign property</h2><label>Department officer<select required value={targetOfficer} onChange={event => setTargetOfficer(event.target.value)}><option value="">Select officer</option>{officers.filter(item => item.is_active && item.role !== 'DEPARTMENT_ADMIN').map(item => <option key={item.officer_id} value={item.officer_id}>{item.name}</option>)}</select></label><label>Property ID or parcel ID<input required value={propertyId} onChange={event => setPropertyId(event.target.value.toUpperCase())} placeholder="P1001"/></label><label>Reassign from (optional)<select value={previousOfficer} onChange={event => setPreviousOfficer(event.target.value)}><option value="">New assignment</option>{officers.filter(item => item.is_active && item.role !== 'DEPARTMENT_ADMIN').map(item => <option key={item.officer_id} value={item.officer_id}>{item.name}</option>)}</select></label><button type="submit" disabled={!targetOfficer || !propertyId}>Save assignment</button></form>
    </div>
    <section className="officer-admin-section"><header><h2>Department officers</h2><span>{officers.length} accounts</span></header>{loading ? <div className="officer-admin-loading"><Activity/> Loading department records</div> : <div className="officer-admin-table-wrap"><table><thead><tr><th>Name</th><th>Officer ID</th><th>Role</th><th>Last login</th><th>Status</th><th/></tr></thead><tbody>{officers.map(officer => <tr key={officer.officer_id}><td><strong>{officer.name}</strong><small>{officer.email}</small></td><td>{officer.officer_id.slice(0, 8)}</td><td>{officer.designation || officer.role.replace(/_/g, ' ')}</td><td>{officer.last_login ? new Date(officer.last_login).toLocaleDateString() : 'Never'}</td><td>{officer.is_active ? 'Active' : 'Inactive'}</td><td>{officer.role !== 'DEPARTMENT_ADMIN' && <button type="button" onClick={() => void toggleActive(officer)}>{officer.is_active ? 'Deactivate' : 'Activate'}</button>}</td></tr>)}</tbody></table></div>}</section>
    <section className="officer-admin-section"><header><h2>Assigned records</h2><span>{assignments.length} records</span></header><div className="officer-admin-table-wrap"><table><thead><tr><th>Property</th><th>Parcel</th><th>Assigned officer</th><th>Status</th></tr></thead><tbody>{assignments.map(item => <tr key={item.assignment_id}><td>{item.property_id}</td><td>{item.parcel_id}</td><td>{item.officer_name}</td><td>{item.is_active ? 'Active' : 'Inactive'}</td></tr>)}</tbody></table></div></section>
    <section className="officer-admin-section"><header><h2>Officer activity</h2><span>Latest {activity.length}</span></header><div className="officer-admin-table-wrap"><table><thead><tr><th>Action</th><th>Record</th><th>Officer</th><th>When</th></tr></thead><tbody>{activity.map((item, index) => <tr key={`${item.record_id}-${index}`}><td>{item.action}</td><td>{item.record_id}</td><td>{item.officer_id?.slice(0, 8) || '—'}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div></section>
  </main>;
}
