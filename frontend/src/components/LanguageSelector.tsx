import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Globe2, Search, X } from 'lucide-react';
import { languages } from '../i18n/languages';
import { useTranslation } from '../i18n';

export default function LanguageSelector() {
  const { language, setLanguage, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => { const close = (event: MouseEvent) => { if (root.current && !root.current.contains(event.target as Node)) setOpen(false); }; document.addEventListener('mousedown', close); return () => document.removeEventListener('mousedown', close); }, []);
  const filtered = languages.filter(item => `${item.name} ${item.nativeName}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="language-selector" ref={root}>
    <button className="language-trigger" type="button" aria-haspopup="listbox" aria-expanded={open} aria-label={`${t('language')}: ${language.nativeName}`} onClick={() => setOpen(value => !value)}><Globe2 size={16}/><span className="language-trigger-copy"><strong>{language.nativeName}</strong><small>{language.name}</small></span><ChevronDown size={14} className={open ? 'language-chevron open' : 'language-chevron'}/></button>
    {open && <div className="language-menu" role="dialog" aria-label={t('chooseLanguage')}><div className="language-menu-head"><strong>{t('chooseLanguage')}</strong><button type="button" aria-label="Close" onClick={() => setOpen(false)}><X size={15}/></button></div><label className="language-search"><Search size={15}/><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder={t('searchLanguages')} /></label><div className="language-options" role="listbox">{(['scheduled', 'extended'] as const).map(group => <div key={group} className="language-group"><span>{t(group === 'scheduled' ? 'scheduledLanguages' : 'extendedLanguages')}</span>{filtered.filter(item => item.group === group).map(item => <button key={item.code} type="button" role="option" aria-selected={item.code === language.code} className={item.code === language.code ? 'selected' : ''} onClick={() => { setLanguage(item.code); setOpen(false); setQuery(''); }}><span><strong lang={item.code} dir={item.direction}>{item.nativeName}</strong><small>{item.name}</small></span>{item.code === language.code && <Check size={15}/>}</button>)}</div>)}{!filtered.length && <p className="language-empty">{t('noLanguages')}</p>}</div></div>}
  </div>;
}
