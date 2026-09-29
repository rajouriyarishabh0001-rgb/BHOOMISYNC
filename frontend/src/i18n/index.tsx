import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { defaultLanguage, findLanguage, type LanguageDefinition } from './languages';

export type TranslationValues = Record<string, string | number>;
type TranslationMap = Record<string, string>;
type LocaleModule = { default: TranslationMap };

const localeModules = import.meta.glob<LocaleModule>('./locales/*/common.json');
const englishFallback: TranslationMap = {
  appName: 'BHOOMISYNC', search: 'Search', home: 'Home', map: 'Map', records: 'Records', conflicts: 'Conflicts', updates: 'Land updates', schemes: 'Schemes', overview: 'Overview', gisWorkspace: 'GIS workspace', dataSources: 'Data sources', aiMatching: 'AI matching', satellite: 'Satellite', verification: 'Verification', reports: 'Reports', officerPortal: 'Officer portal', publicInformation: 'Public information', viewCitizenPortal: 'View citizen portal', officerWorkspace: 'Officer workspace', systemsOnline: 'Systems online', language: 'Language', scheduledLanguages: 'Scheduled languages', extendedLanguages: 'Additional Indian languages', chooseLanguage: 'Choose language', searchLanguages: 'Search languages', noLanguages: 'No languages found', officerAccess: 'Officer access', officerLogin: 'Officer Login', signIn: 'Sign In', password: 'Password', email: 'Officer ID / Email', rememberMe: 'Remember me on this device', forgotPassword: 'Forgot Password?', signInSecurely: 'Signing in securely', loginSuccess: 'Authentication successful. Opening dashboard...', invalidCredentials: 'Invalid Officer ID or password.', enterEmail: 'Enter your Officer ID or email.', enterPassword: 'Enter your password.', dashboard: 'Dashboard', properties: 'Properties', satelliteImagery: 'Satellite Imagery', gisMap: 'GIS Map', auditLogs: 'Audit Logs', settings: 'Settings', parcel: 'Parcel', surveyNumber: 'Survey Number', khasraNumber: 'Khasra Number', ownerName: 'Owner Name', location: 'Location', latitude: 'Latitude', longitude: 'Longitude', district: 'District', tehsil: 'Tehsil', village: 'Village', ward: 'Ward', zone: 'Zone', area: 'Area', verificationStatus: 'Verification Status', conflictStatus: 'Conflict Status', propertyStatus: 'Property Status', landUse: 'Land Use', dataSource: 'Data Source', loading: 'Loading...', error: 'Something went wrong.', noResults: 'No results found.'
};

const context = createContext<{ language: LanguageDefinition; setLanguage: (code: string) => void; t: (key: string, values?: TranslationValues) => string }>({ language: findLanguage(defaultLanguage)!, setLanguage: () => undefined, t: key => englishFallback[key] ?? key });

function browserLanguage() { const code = navigator.language?.split('-')[0] ?? defaultLanguage; return findLanguage(code) ? code : defaultLanguage; }

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [code, setCode] = useState(() => { const saved = localStorage.getItem('language'); return saved && findLanguage(saved) ? saved : browserLanguage(); });
  const [translations, setTranslations] = useState<TranslationMap>({});
  const language = findLanguage(code)!;

  useEffect(() => {
    localStorage.setItem('language', code);
    document.documentElement.lang = code;
    document.documentElement.dir = language.direction;
    const path = `./locales/${code}/common.json`;
    const loader = localeModules[path];
    if (!loader) { setTranslations({}); return; }
    loader().then(module => setTranslations(module.default)).catch(() => setTranslations({}));
  }, [code, language.direction]);

  const setLanguage = (next: string) => { if (findLanguage(next)) setCode(next); };
  const t = (key: string, values?: TranslationValues) => { let value = translations[key] ?? englishFallback[key] ?? key; Object.entries(values ?? {}).forEach(([name, replacement]) => { value = value.replace(`{{${name}}}`, String(replacement)); }); return value; };
  return <context.Provider value={{ language, setLanguage, t }}>{children}</context.Provider>;
}

export const useTranslation = () => useContext(context);
