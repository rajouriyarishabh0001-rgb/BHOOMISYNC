const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export type Property = {
  parcel_id: string; owner_name: string; property_id?: string; area_sq_m?: number; area_sq_ft?: number;
  land_use?: string; property_type?: string; address?: string; ward?: number; district?: string; state?: string;
  latitude?: number; longitude?: number; verification_status?: string; conflict_status?: string; match_score?: number;
  geometry?: GeoJSON.Geometry; geojson?: GeoJSON.Feature; [key: string]: unknown;
};
type Breakdown = { name: string; value: number };
export type DashboardStats = {
  total_properties: number; records_processed: number; ai_matches: number; potential_conflicts: number;
  requires_review: number; verified: number; gis_parcels: number; satellite_observations: number;
  source_breakdown: Breakdown[]; verification_breakdown: Breakdown[]; land_use_breakdown: Breakdown[];
};
export type OfficerProfile = {
  id: string; officer_id: string; name: string; email: string; role: string; department: string;
  department_key: string | null; permissions: string[]; designation: string; assigned_record_count: number;
};
export function officerHomePath(department: string | null | undefined) {
  const routes: Record<string, string> = {
    municipal: '/officer/municipal', registration: '/officer/registration', revenue: '/officer/revenue',
    electricity: '/officer/electricity', property_tax: '/officer/property-tax', gis: '/officer/gis', planning: '/officer/planning',
  };
  return routes[department || ''] || '/officer/dashboard';
}

let accessToken = localStorage.getItem("bhoomisync_access_token") || "";
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(detail?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
function json<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
}
function featureToProperty(feature: GeoJSON.Feature): Property | null {
  if (!feature.geometry) return null;
  const coordinates = feature.geometry.type === "Point" ? feature.geometry.coordinates : undefined;
  return { ...(feature.properties || {}), parcel_id: String(feature.properties?.parcel_id || "unknown"), owner_name: String(feature.properties?.owner_name || "Property"), latitude: coordinates?.[1] ?? feature.properties?.latitude, longitude: coordinates?.[0] ?? feature.properties?.longitude, geometry: feature.geometry };
}

export const api = {
  search: (query: string) => json<{ items: Property[]; results: Property[] }>("/api/search", { query }),
  properties: (page = 1, pageSize = 25) => request<{ items: Property[]; total: number; page: number; page_size: number }>(`/api/properties?page=${page}&page_size=${pageSize}`),
  property: (parcelId: string) => request<Property>(`/api/properties/${encodeURIComponent(parcelId)}`),
  stats: () => request<DashboardStats>("/api/dashboard/stats"),
  conflicts: () => request<{ items: unknown[] }>("/api/conflicts"),
  sources: () => request<{ items: unknown[] }>("/api/sources"),
  resources: (type: string) => request<{ items: unknown[] }>(`/api/land-resources/${encodeURIComponent(type)}`),
  mapConfig: () => request<Record<string, unknown>>("/api/maps/config"),
  satelliteLayers: () => request<Record<string, unknown>>("/api/satellite/layers"),
  satellite: (parcelId: string) => json<Record<string, unknown>>("/api/satellite/analyze", { parcel_id: parcelId }),
  scan: (parcelId: string) => json<Record<string, unknown>>(`/api/property/${encodeURIComponent(parcelId)}/scan`),
  nearby: (latitude: number, longitude: number, radius: number) => request<{ items: Property[] }>(`/api/properties/nearby?latitude=${latitude}&longitude=${longitude}&radius=${radius}`),
  viewport: async (bounds: { north: number; south: number; east: number; west: number }) => {
    const query = new URLSearchParams(Object.entries(bounds).map(([key, value]) => [key, String(value)]));
    const data = await request<GeoJSON.FeatureCollection>(`/api/maps/viewport?${query}`);
    return { items: data.features.map(featureToProperty).filter((item): item is Property => Boolean(item)) };
  },
  uploadDataset: async (file: File) => {
    const form = new FormData(); form.append("file", file);
    const result = await request<{ status?: string; filename?: string; bytes?: number }>("/api/upload", { method: "POST", body: form });
    return { data: { ...result, processing_status: result.status || "UPLOADED" } };
  },
  officerLogin: async (credentials: { email: string; password: string }) => {
    const result = await json<{ success: boolean; data: { access_token: string; user: OfficerProfile } }>("/api/officer/auth/login", credentials);
    accessToken = result.data.access_token; localStorage.setItem("bhoomisync_access_token", accessToken); return result;
  },
  officerMe: () => request<{ success: boolean; data: OfficerProfile & { is_verified: boolean } }>("/api/officer/me"),
  officerLogout: async () => {
    try { await request<{ success: boolean }>("/api/officer/auth/logout", { method: "POST" }); }
    finally { accessToken = ""; localStorage.removeItem("bhoomisync_access_token"); }
  },
  officerDepartments: () => request<{ success: boolean; data: Array<{ key: string; title: string; route: string; description: string }> }>("/api/officer/departments"),
  officerDepartmentSummary: (department: string) => request<{ success: boolean; data: { department: string; title: string; stats: Record<string, number>; records: unknown[] } }>(`/api/officer/departments/${encodeURIComponent(department)}`),
  officerProperty: (propertyId: string) => request<{ success: boolean; data: { property: Property; departments: Record<string, { record_status?: string; assigned_officer?: string; last_updated?: string; verification_status?: string; records: unknown[] }> } }>(`/api/officer/property/${encodeURIComponent(propertyId)}`),
  officerVerify: (parcelId: string, status: string, remarks: string) => json<Record<string, unknown>>(`/api/officer/properties/${encodeURIComponent(parcelId)}/verify`, { status, remarks }),
  officerFlag: (parcelId: string, description: string) => json<Record<string, unknown>>(`/api/officer/properties/${encodeURIComponent(parcelId)}/flag`, { description, conflict_type: 'OFFICER_FLAG', severity: 'MEDIUM' }),
  officerAdminOfficers: () => request<{ success: boolean; data: Array<{ officer_id: string; name: string; email: string; role: string; designation?: string; is_active: boolean; last_login?: string }> }>("/api/officer/admin/officers"),
  officerAdminCreate: (payload: { name: string; email: string; password: string; designation?: string }) => json<{ success: boolean; data: { officer_id: string } }>("/api/officer/admin/officers", payload),
  officerAdminSetActive: (officerId: string, isActive: boolean) => request<Record<string, unknown>>(`/api/officer/admin/officers/${encodeURIComponent(officerId)}/active`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: isActive }) }),
  officerAdminAssignments: () => request<{ success: boolean; data: Array<{ assignment_id: string; officer_id: string; officer_name: string; property_id: string; parcel_id: string; is_active: boolean }> }>("/api/officer/admin/assignments"),
  officerAdminAssign: (payload: { officer_id: string; property_id: string; from_officer_id?: string }) => json<Record<string, unknown>>("/api/officer/admin/assignments", payload),
  officerAdminStats: () => request<{ success: boolean; data: { department: string; officers: number; active_assignments: number } }>("/api/officer/admin/stats"),
  officerAdminActivity: () => request<{ success: boolean; data: Array<{ officer_id?: string; action: string; record_id: string; reason?: string; created_at: string }> }>("/api/officer/admin/activity"),
  forgotPassword: (email: string) => json<{ message: string; reset_token?: string | null }>("/api/auth/forgot-password", { email }),
  createPassword: (token: string, password: string) => json<{ message: string }>("/api/auth/create-password", { token, password }),
  officerGisLayers: () => request<{ success: boolean; data: unknown[] }>("/api/officer/gis/layers"),
  officerGisParcel: (parcelId: string) => request<{ success: boolean; data: Property }>(`/api/officer/gis/parcel/${encodeURIComponent(parcelId)}`),
  officerGisViewport: async (bounds: { north: number; south: number; east: number; west: number }) => {
    const query = new URLSearchParams(Object.entries(bounds).map(([key, value]) => [key, String(value)]));
    const result = await request<{ success: boolean; data: Property[] }>(`/api/officer/gis/viewport?${query}`);
    return { items: result.data };
  },
  officerGisNearby: async (latitude: number, longitude: number, radius: number) => {
    const query = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude), radius: String(radius) });
    const result = await request<{ success: boolean; data: Property[] }>(`/api/officer/gis/nearby?${query}`);
    return { items: result.data };
  },
  officerSatelliteHistory: (parcelId: string) => request<{ items: unknown[] }>(`/api/officer/satellite/history/${encodeURIComponent(parcelId)}`),
};
