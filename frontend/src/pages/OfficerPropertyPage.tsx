import { useEffect, useState } from 'react';
import { Activity, ArrowLeft, BadgeCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import './OfficerPropertyPage.css';
import './OfficerPropertyMeta.css';

type PropertyResponse = Awaited<ReturnType<typeof api.officerProperty>>['data'];

export default function OfficerPropertyPage() {
  const { propertyId = '' } = useParams();
  const [data, setData] = useState<PropertyResponse | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api.officerProperty(propertyId).then(result => { if (active) setData(result.data); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Property record could not be loaded.'); });
    return () => { active = false; };
  }, [propertyId]);

  if (error) return <div className="officer-property-state"><BadgeCheck/><h2>Property unavailable</h2><p>{error}</p><Link to="/officer/dashboard">Back to dashboard</Link></div>;
  if (!data) return <div className="officer-property-state"><Activity className="officer-property-spin"/><span>Loading authorized property information...</span></div>;

  return <main className="officer-property-page">
    <Link className="officer-property-back" to="/officer/dashboard"><ArrowLeft size={15}/> Department dashboard</Link>
    <header className="officer-property-header"><div><span>UNIFIED PROPERTY RECORD</span><h1>{data.property.property_id || data.property.parcel_id}</h1><p>{data.property.owner_name} · {data.property.address || 'Address not provided'}</p></div><div className="officer-property-status">{data.property.verification_status || 'STATUS UNAVAILABLE'}</div></header>
    <section className="officer-property-summary"><div><span>Parcel</span><strong>{data.property.parcel_id}</strong></div><div><span>Area</span><strong>{data.property.area_sq_m?.toLocaleString() ?? '—'} m²</strong></div><div><span>Land use</span><strong>{data.property.land_use || '—'}</strong></div><div><span>Ward / district</span><strong>{[data.property.ward, data.property.district].filter(Boolean).join(' / ') || '—'}</strong></div></section>
    <div className="officer-property-sections">{Object.entries(data.departments).map(([department, section]) => <section className="officer-property-section" key={department}>
      <header><div><span>DEPARTMENT RECORD</span><h2>{department.replace(/_/g, ' ')}</h2></div><div className="officer-property-section-status"><span><small>Verification</small><strong>{section.verification_status || 'Not recorded'}</strong></span><span><small>Assigned officer</small><strong>{section.assigned_officer || 'Not assigned'}</strong></span><span><small>Record status</small><strong>{section.record_status || 'Not recorded'}</strong></span><span><small>Last updated</small><strong>{section.last_updated ? new Date(section.last_updated).toLocaleString() : 'Not recorded'}</strong></span></div></header>
      {section.records.length ? <div className="officer-property-records">{section.records.map((record, index) => <dl key={index}>{Object.entries(record as Record<string, unknown>).filter(([, value]) => value !== null && value !== undefined && value !== '').map(([key, value]) => <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>)}</div> : <p className="officer-property-empty">No authorized departmental source record is linked.</p>}
    </section>)}</div>
  </main>;
}
