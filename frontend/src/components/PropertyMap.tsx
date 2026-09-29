import { useEffect, useRef, useState } from 'react';
import { GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import { importLibrary, setOptions } from '@googlemaps/js-api-loader';
import L from 'leaflet';
import { Link, useSearchParams } from 'react-router-dom';
import { Activity, Layers3, MapPin, Navigation, Search, Satellite, X } from 'lucide-react';
import { api, Property } from '../services/api';

function FitSelected({ geometry, latitude, longitude, focusToken }: { geometry: any; latitude?: number; longitude?: number; focusToken?: number }) {
  const map = useMap();
  useEffect(() => {
    if (geometry?.coordinates) {
      const layer = L.geoJSON(geometry);
      if (layer?.getBounds?.().isValid()) map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 18 });
    } else if (latitude && longitude) {
      map.setView([latitude, longitude], 18);
    }
  }, [geometry, latitude, longitude, focusToken, map]);
  return null;
}

function ViewportLoader({ onLoad, officer }: { onLoad: (items: Property[]) => void; officer: boolean }) {
  const map = useMap();
  useEffect(() => {
    const load = () => {
      const bounds = map.getBounds();
      const extent = { north: bounds.getNorth(), south: bounds.getSouth(), east: bounds.getEast(), west: bounds.getWest() };
      (officer ? api.officerGisViewport(extent) : api.viewport(extent)).then(result => onLoad(result.items)).catch(() => onLoad([]));
    };
    load();
    map.on('moveend', load);
    return () => { map.off('moveend', load); };
  }, [map, onLoad, officer]);
  return null;
}

function GoogleMapView({ mode, selectedId, onSelect, onLoad, officer }: { mode: 'street' | 'satellite' | 'hybrid' | 'terrain'; selectedId: string | null; onSelect: (parcelId: string) => void; onLoad: (items: Property[]) => void; officer: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map>();
  const markersRef = useRef<google.maps.Marker[]>([]);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  useEffect(() => {
    if (!containerRef.current || !apiKey) return;
    let cancelled = false;
    setOptions({ key: apiKey, v: 'weekly' });
    importLibrary('maps').then(({ Map }) => {
      if (cancelled || !containerRef.current) return;
      mapRef.current = new Map(containerRef.current, { center: { lat: 23.525, lng: 77.808 }, zoom: 13, mapTypeId: mode === 'street' ? 'roadmap' : mode === 'hybrid' ? 'hybrid' : mode === 'terrain' ? 'terrain' : 'satellite', mapTypeControl: false, streetViewControl: false, fullscreenControl: false });
      const loadViewport = () => {
        const bounds = mapRef.current?.getBounds();
        if (!bounds) return;
        const northeast = bounds.getNorthEast();
        const southwest = bounds.getSouthWest();
        const extent = { north: northeast.lat(), south: southwest.lat(), east: northeast.lng(), west: southwest.lng() };
        (officer ? api.officerGisViewport(extent) : api.viewport(extent)).then(result => onLoad(result.items)).catch(() => onLoad([]));
      };
      mapRef.current.addListener('idle', loadViewport);
      loadViewport();
    }).catch(() => onLoad([]));
    return () => { cancelled = true; markersRef.current.forEach(marker => marker.setMap(null)); markersRef.current = []; };
  }, [apiKey, mode, onLoad, officer]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const bounds = map.getBounds();
    if (!bounds) return;
    const extent = { north: bounds.getNorthEast().lat(), south: bounds.getSouthWest().lat(), east: bounds.getNorthEast().lng(), west: bounds.getSouthWest().lng() };
    (officer ? api.officerGisViewport(extent) : api.viewport(extent)).then(result => {
      markersRef.current.forEach(marker => marker.setMap(null));
      markersRef.current = result.items.filter(item => item.latitude !== undefined && item.longitude !== undefined).map(item => {
        const marker = new google.maps.Marker({ map, position: { lat: item.latitude!, lng: item.longitude! }, title: `${item.parcel_id} · ${item.owner_name}` });
        marker.addListener('click', () => onSelect(item.parcel_id));
        return marker;
      });
      const selected = result.items.find(item => item.parcel_id === selectedId);
      if (selected?.latitude !== undefined && selected.longitude !== undefined) map.panTo({ lat: selected.latitude, lng: selected.longitude });
    }).catch(() => undefined);
  }, [selectedId, onSelect, officer]);

  return <div ref={containerRef} className="google-map" style={{ height: '100%', width: '100%' }} aria-label="Google property map" />;
}

export default function PropertyMap({ mode = 'street', config, officer = false, onModeChange }: { mode?: 'street' | 'satellite' | 'hybrid' | 'terrain'; config?: any; officer?: boolean; onModeChange?: (mode: 'street' | 'satellite' | 'hybrid' | 'terrain') => void }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('parcel');
  const [selected, setSelected] = useState<any>();
  const [nearby, setNearby] = useState<Property[]>([]);
  const [viewportProperties, setViewportProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(Boolean(selectedId));
  const [message, setMessage] = useState('');
  const [focusToken, setFocusToken] = useState(0);
  const [userLocation, setUserLocation] = useState<[number, number]>();
  const [satelliteOpacity, setSatelliteOpacity] = useState(.85);
  const [satelliteError, setSatelliteError] = useState(false);
  const [localMode, setLocalMode] = useState(mode);
  const activeMode = onModeChange ? mode : localMode;
  useEffect(() => setLocalMode(mode), [mode]);
  const googleKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const satelliteTileUrl = import.meta.env.VITE_SATELLITE_TILE_URL || 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
  const satelliteAttribution = import.meta.env.VITE_SATELLITE_ATTRIBUTION || '© Esri, Maxar, Earthstar Geographics, and the GIS User Community';

  useEffect(() => {
    if (!selectedId) { setSelected(undefined); setLoading(false); return; }
    setLoading(true); setMessage('');
    (officer ? api.officerGisParcel(selectedId).then(result => result.data) : api.property(selectedId)).then(setSelected).catch(() => { setSelected(undefined); setMessage('Property not found or not assigned to this officer.'); }).finally(() => setLoading(false));
  }, [selectedId]);

  const selectParcel = (parcelId: string) => setSearchParams({ parcel: parcelId });
  const locateProperty = () => {
    if (!selected) { setMessage('Select a property first.'); return; }
    setFocusToken(value => value + 1);
  };
  const searchNearby = () => {
    if (!selected?.latitude || !selected?.longitude) { setMessage('Property location is unavailable.'); return; }
    (officer ? api.officerGisNearby(selected.latitude, selected.longitude, 500) : api.nearby(selected.latitude, selected.longitude, 500)).then(result => setNearby(result.items)).catch(() => setMessage('Nearby properties are unavailable.'));
  };
  const locateMe = () => {
    navigator.geolocation.getCurrentPosition(position => {
      setUserLocation([position.coords.latitude, position.coords.longitude]);
      (officer ? api.officerGisNearby(position.coords.latitude, position.coords.longitude, 1000) : api.nearby(position.coords.latitude, position.coords.longitude, 1000)).then(result => setNearby(result.items));
    }, () => setMessage('Location permission was not granted.'));
  };

  return <div className="property-map-shell">
    {googleKey ? <GoogleMapView mode={activeMode === 'terrain' ? 'street' : activeMode} selectedId={selectedId} onSelect={selectParcel} onLoad={setViewportProperties} officer={officer} /> : <MapContainer center={[23.525, 77.808]} zoom={13} scrollWheelZoom className="leaflet-map">
      {activeMode === 'satellite' || activeMode === 'hybrid' ? <TileLayer key="satellite" url={satelliteTileUrl} attribution={satelliteAttribution} opacity={activeMode === 'satellite' ? satelliteOpacity : .72} eventHandlers={{ tileerror: () => setSatelliteError(true), tileload: () => setSatelliteError(false) }} /> : <TileLayer key="street" url={config?.street?.tile_url || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'} attribution="© OpenStreetMap contributors" />}
      <ViewportLoader onLoad={setViewportProperties} officer={officer} />
      {selected && <FitSelected geometry={selected.geometry || selected.geojson?.geometry} latitude={selected.latitude} longitude={selected.longitude} focusToken={focusToken} />}
      {viewportProperties.filter(item => item.latitude !== undefined && item.longitude !== undefined).map(item => <Marker key={item.parcel_id} position={[item.latitude!, item.longitude!]} eventHandlers={{ click: () => selectParcel(item.parcel_id) }} />)}
      {nearby.filter(item => item.latitude !== undefined && item.longitude !== undefined).map(item => <Marker key={`nearby-${item.parcel_id}`} position={[item.latitude!, item.longitude!]} eventHandlers={{ click: () => selectParcel(item.parcel_id) }} />)}
      {nearby.filter(item => item.geometry && item.parcel_id !== selected?.parcel_id).map(item => <GeoJSON key={`boundary-${item.parcel_id}`} data={item.geometry!} style={{ color: '#718096', weight: 1, fillColor: '#cbd5e1', fillOpacity: .12 }} eventHandlers={{ click: () => selectParcel(item.parcel_id) }} />)}
      {selected?.geometry && <GeoJSON data={selected.geometry} style={{ color: '#2464e8', weight: 4, fillColor: '#2464e8', fillOpacity: .24 }} />}
      {userLocation && <Marker position={userLocation}><Popup>You are here</Popup></Marker>}
      {selected?.latitude && <Marker position={[selected.latitude, selected.longitude]}><Popup>
        <div className="map-popup"><strong>{selected.parcel_id}</strong><span><b>Owner</b>{selected.owner_name}</span><span><b>Area</b>{selected.area_sq_m?.toLocaleString()} sq.m</span><span><b>Land use</b>{selected.land_use}</span><span>{selected.address}</span><div className="popup-actions"><Link to={`/${officer ? 'officer' : 'user'}/property/${selected.parcel_id}`}>View Details</Link><button onClick={searchNearby}><Search size={13}/> Search Nearby</button></div></div>
      </Popup></Marker>}
    </MapContainer>}
    <div className="map-toolbar"><span className="map-title"><MapPin size={15}/> Property map</span>{selected&&<button onClick={locateProperty}><MapPin size={13}/> Locate Property</button>}<button onClick={locateMe}><Navigation size={13}/> My Location</button>{selected && <button onClick={() => setSearchParams({})}><X size={13}/> Clear</button>}</div>
    <div className="map-layer-switcher"><div className="map-layer-title"><Layers3 size={14}/> Map Type</div>{(['street','satellite','hybrid','terrain'] as const).map(layer=><label key={layer}><input type="radio" name={`map-type-${officer ? 'officer' : 'public'}`} checked={activeMode === layer} onChange={() => onModeChange ? onModeChange(layer) : setLocalMode(layer)}/><span>{layer === 'satellite' ? <Satellite size={13}/> : <MapPin size={13}/>} {layer[0].toUpperCase() + layer.slice(1)}</span></label>)}{(activeMode === 'satellite' || activeMode === 'hybrid') && <label className="opacity-control"><span>Satellite opacity <b>{Math.round(satelliteOpacity * 100)}%</b></span><input type="range" min="0" max="100" value={satelliteOpacity * 100} onChange={event => setSatelliteOpacity(Number(event.target.value) / 100)}/></label>}<small>Satellite Imagery<br/>Source: {googleKey ? 'Google Maps' : 'Esri World Imagery'}</small></div>
    {loading && <div className="map-loading"><Activity className="spin" size={16}/> Loading parcel...</div>}
    {message && <div className="map-status"><span>{message}</span></div>}
    {satelliteError && (activeMode === 'satellite' || activeMode === 'hybrid') && <div className="map-status satellite-error">Satellite imagery could not be loaded. Please check the imagery provider configuration.</div>}
    <div className="citizen-map-legend"><span><i className="legend-boundary"/> Property Boundary</span><span><i className="legend-location"/> Property Location</span><span><i className="legend-warning">!</i> Information Requires Verification</span></div>
    {selected && <aside className="selected-property-panel"><div className="panel-heading"><div><small>PROPERTY DETAILS / संपत्ति विवरण</small><h3>{selected.parcel_id}</h3></div><button onClick={() => setSearchParams({})} aria-label="Close property panel"><X size={16}/></button></div><p className="owner-name">{selected.owner_name}</p><dl><div><dt>Parcel ID / पार्सल आईडी</dt><dd>{selected.parcel_id}</dd></div><div><dt>Survey Number / सर्वे नंबर</dt><dd>{selected.survey_number || 'Unavailable'}</dd></div><div><dt>Khasra Number / खसरा नंबर</dt><dd>{selected.khasra_number || 'Unavailable'}</dd></div><div><dt>Area / क्षेत्रफल</dt><dd>{selected.area_sq_m?.toLocaleString()} sq.m</dd></div><div><dt>Land Use / भूमि उपयोग</dt><dd>{selected.land_use || 'Unavailable'}</dd></div><div><dt>Address / पता</dt><dd>{selected.address || 'Unavailable'}</dd></div><div><dt>Status</dt><dd>{selected.verification_status || 'Available'}</dd></div></dl>{selected.conflict_status==='OPEN'&&<div className="public-warning">Some information from available records differs. Please verify with the concerned authority.</div>}{mode!=='street'&&<div className="public-warning">Satellite imagery is for visual reference only.</div>}<div className="panel-actions"><Link to={`/${officer ? 'officer' : 'user'}/property/${selected.parcel_id}`}>View Full Property Details</Link><button onClick={searchNearby}><Search size={14}/> Search Nearby</button></div></aside>}
  </div>;
}
