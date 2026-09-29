import { useEffect, useState } from 'react';
import { Activity, ArrowRight, BadgeCheck, Map, RefreshCw } from 'lucide-react';
import { Link, Navigate } from 'react-router-dom';
import PropertyMap from '../components/PropertyMap';
import { api, OfficerProfile, officerHomePath } from '../services/api';
import './OfficerDepartmentDashboard.css';
import './OfficerDepartmentActions.css';

type DepartmentKey = 'municipal' | 'registration' | 'revenue' | 'electricity' | 'property_tax' | 'gis' | 'planning';
type DashboardData = { department: string; title: string; stats: Record<string, number>; records: Record<string, any>[] };

const dashboards: Record<DepartmentKey, { title: string; kpis: string[]; columns: string[] }> = {
  municipal: { title: 'Municipal Department Dashboard', kpis: ['Total Assigned Properties', 'Verified Properties', 'Pending Verification', 'Potential Conflicts', 'Recently Updated'], columns: ['parcel_id', 'property_id', 'owner_name', 'address', 'ward', 'property_type', 'land_use', 'plot_area', 'built_up_area', 'verification_status'] },
  registration: { title: 'Registration / Nomination Department', kpis: ['Total Assigned Registrations', 'Pending Verification', 'Verified', 'Pending Documents', 'Potential Conflicts'], columns: ['source_record_id', 'parcel_id', 'document_number', 'owner_name', 'party_names', 'survey_number', 'khasra_number', 'area_original', 'registration_date', 'property_type'] },
  revenue: { title: 'Collectorate / Revenue Dashboard', kpis: ['Assigned Revenue Records', 'Pending Mutation', 'Verified Records', 'Potential Conflicts', 'Missing Information'], columns: ['parcel_id', 'property_id', 'owner_name', 'village', 'tehsil', 'district', 'survey_number', 'khasra_number', 'area_original', 'land_classification', 'mutation_status'] },
  electricity: { title: 'Electricity Department Dashboard', kpis: ['Total Connections', 'Active Connections', 'Pending Verification', 'Billing Issues', 'Property Conflicts'], columns: ['source_record_id', 'parcel_id', 'consumer_number', 'owner_name', 'meter_number', 'category', 'connection_status', 'sanctioned_load_kw', 'address'] },
  property_tax: { title: 'Property Tax Department Dashboard', kpis: ['Total Assigned Properties', 'Tax Assessed', 'Pending Payments', 'Total Due', 'Verified Records', 'Potential Conflicts'], columns: ['source_record_id', 'parcel_id', 'owner_name', 'assessment_year', 'category', 'assessed_area', 'tax_amount', 'tax_status', 'address'] },
  gis: { title: 'GIS / Survey Dashboard', kpis: ['Total Assigned Parcels', 'Verified Parcels', 'Boundary Variations', 'Missing Geometry', 'Potential GIS Conflicts'], columns: ['parcel_id', 'owner_name', 'survey_number', 'khasra_number', 'area_sq_m', 'land_use', 'verification_status'] },
  planning: { title: 'Urban Planning Dashboard', kpis: ['Assigned Properties', 'Planning Reviews', 'Zoning Conflicts', 'Pending Approvals', 'Verified Properties'], columns: ['source_record_id', 'parcel_id', 'owner_name', 'planning_zone', 'land_use', 'development_zone', 'restrictions'] },
};

const departmentNames: Record<DepartmentKey, string> = {
  municipal: 'Municipal', registration: 'Registration', revenue: 'Revenue', electricity: 'Electricity', property_tax: 'Property Tax', gis: 'GIS / Survey', planning: 'Urban Planning',
};
const metricKeys: Record<DepartmentKey, string[]> = {
  municipal: ['total_records', 'verified_records', 'pending_verification', 'open_conflicts', 'recently_updated'],
  registration: ['total_records', 'pending_verification', 'verified_records', 'pending_documents', 'open_conflicts'],
  revenue: ['total_records', 'pending_mutation', 'verified_records', 'open_conflicts', 'missing_information'],
  electricity: ['total_records', 'active_connections', 'pending_verification', 'billing_issues', 'open_conflicts'],
  property_tax: ['total_records', 'tax_assessed', 'pending_payments', 'total_due', 'verified_records', 'open_conflicts'],
  gis: ['total_records', 'verified_records', 'boundary_variations', 'missing_geometry', 'open_conflicts'],
  planning: ['total_records', 'planning_reviews', 'open_conflicts', 'pending_approvals', 'verified_records'],
};

export function OfficerDashboardEntry() {
  const [profile, setProfile] = useState<OfficerProfile | null>(null);
  useEffect(() => { api.officerMe().then(result => setProfile(result.data)).catch(() => setProfile(null)); }, []);
  if (!profile) return <div className="officer-department-state"><Activity className="officer-refresh-spin"/><span>Loading authenticated department...</span></div>;
  const destination = profile.department_key ? officerHomePath(profile.department_key) : profile.role.includes('ADMIN') ? '/officer/reports' : '/officer/login';
  return <Navigate to={destination} replace/>;
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function OfficerDepartmentDashboard({ department }: { department: DepartmentKey }) {
  const [profile, setProfile] = useState<OfficerProfile | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [mapConfig, setMapConfig] = useState<Record<string, unknown> | undefined>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [verifying, setVerifying] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  const load = async () => {
    setRefreshing(true);
    setError('');
    try {
      const result = await api.officerDepartmentSummary(department);
      setDashboard(result.data as DashboardData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Department records could not be loaded.');
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    Promise.all([api.officerMe(), department === 'gis' ? api.mapConfig().catch(() => undefined) : Promise.resolve(undefined)])
      .then(([result, config]) => {
        if (!active) return;
        setProfile(result.data);
        setMapConfig(config);
        void load();
      })
      .catch(() => { if (active) { setLoading(false); setError('Your officer session could not be verified.'); } });
    return () => { active = false; };
  }, [department]);

  if (profile && profile.department_key !== department && !profile.role.includes('ADMIN')) {
    return <Navigate to={profile.department_key ? `/officer/${profile.department_key === 'property_tax' ? 'property-tax' : profile.department_key === 'gis' ? 'gis' : profile.department_key}` : '/officer/login'} replace />;
  }

  const spec = dashboards[department];
  const stats = dashboard?.stats || {};
  const metricValues = metricKeys[department].map(key => Number(stats[key] || 0));
  const verifyRecord = async (record: Record<string, any>) => {
    if (!record.parcel_id) return;
    setVerifying(record.parcel_id);
    setActionMessage('');
    try {
      await api.officerVerify(record.parcel_id, 'VERIFIED', 'Verified from assigned department dashboard');
      setActionMessage(`${record.parcel_id} verification saved.`);
      await load();
    } catch (reason) {
      setActionMessage(reason instanceof Error ? reason.message : 'Verification could not be saved.');
    } finally { setVerifying(''); }
  };
  const flagRecord = async (record: Record<string, any>) => {
    if (!record.parcel_id) return;
    const description = window.prompt(`Describe the potential conflict for ${record.parcel_id}:`);
    if (!description?.trim()) return;
    setVerifying(record.parcel_id);
    setActionMessage('');
    try {
      await api.officerFlag(record.parcel_id, description.trim());
      setActionMessage(`${record.parcel_id} conflict flag saved.`);
      await load();
    } catch (reason) {
      setActionMessage(reason instanceof Error ? reason.message : 'Conflict flag could not be saved.');
    } finally { setVerifying(''); }
  };

  return <main className="officer-department-page">
    <header className="officer-department-heading">
      <div><div className="officer-department-eyebrow">{departmentNames[department].toUpperCase()} / OFFICER WORKSPACE</div><h1>{spec.title}</h1><p>{profile?.name || 'Officer'} · {profile?.designation || profile?.role || 'Department officer'} · {profile?.assigned_record_count ?? 0} assigned records</p></div>
      <button className="officer-refresh" type="button" onClick={() => void load()} disabled={refreshing} aria-label="Refresh dashboard"><RefreshCw size={16} className={refreshing ? 'officer-refresh-spin' : ''}/></button>
    </header>
    <section className="officer-department-kpis" aria-label="Department statistics">
      {spec.kpis.map((label, index) => <article className="officer-kpi" key={label}><span>{label}</span><strong>{metricValues[index] ?? 0}</strong><small>From authorized department records</small></article>)}
    </section>
    {department === 'gis' && <section className="officer-gis-workspace">
      <div className="officer-gis-map"><div className="officer-gis-map-label"><Map size={15}/> ASSIGNED PARCELS <span>DEMO GIS DATA — NOT AN OFFICIAL CADASTRAL MAP</span></div><PropertyMap mode="street" config={mapConfig} officer/></div>
      <div className="officer-gis-disclaimer"><strong>AI Candidate Boundary — Visual Assistance Only</strong><span>Boundary interpretation requires authorized field verification.</span></div>
    </section>}
    <section className="officer-assigned-records">
      <div className="officer-records-heading"><div><div className="officer-department-eyebrow">ASSIGNED WORK QUEUE</div><h2>{department === 'municipal' ? 'My Assigned Properties' : `My ${departmentNames[department]} Records`}</h2></div><span>{dashboard?.records.length || 0} records</span></div>
      {actionMessage && <div className="officer-department-error" role="status">{actionMessage}</div>}
      {loading ? <div className="officer-department-state"><Activity className="officer-refresh-spin"/><span>Loading assigned records...</span></div> : error ? <div className="officer-department-error" role="alert">{error}</div> : dashboard?.records.length ? <div className="officer-table-wrap"><table className="officer-record-table"><thead><tr>{spec.columns.map((column) => <th key={column}>{column.replace(/_/g, ' ')}</th>)}<th>Actions</th></tr></thead><tbody>{dashboard.records.map((record, index) => <tr key={String(record.source_record_id || record.parcel_id || index)}>{spec.columns.map(column => <td key={column}>{column === 'parcel_id' && record.parcel_id ? <Link to={`/officer/property/${encodeURIComponent(record.property_id || record.parcel_id)}`}>{displayValue(record.parcel_id)}</Link> : displayValue(record[column])}</td>)}<td><span className="officer-row-actions"><Link className="officer-view-record" to={`/officer/property/${encodeURIComponent(record.property_id || record.parcel_id || '')}`}>View <ArrowRight size={13}/></Link>{profile?.permissions.includes('VERIFICATION_APPROVE') && record.parcel_id && record.verification_status !== 'VERIFIED' && <button className="officer-verify-record" type="button" disabled={Boolean(verifying)} onClick={() => void verifyRecord(record)}>{verifying === record.parcel_id ? 'Saving...' : 'Verify'}</button>}{profile?.permissions.includes('CONFLICT_VIEW') && record.parcel_id && <button className="officer-flag-record" type="button" disabled={Boolean(verifying)} onClick={() => void flagRecord(record)}>Flag</button>}</span></td></tr>)}</tbody></table></div> : <div className="officer-department-state"><BadgeCheck/><span>No assigned records are available in this department.</span></div>}
    </section>
  </main>;
}
