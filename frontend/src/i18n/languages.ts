export type LanguageDirection = 'ltr' | 'rtl';

export type LanguageDefinition = {
  code: string;
  name: string;
  nativeName: string;
  script: string;
  direction: LanguageDirection;
  group: 'scheduled' | 'extended';
};

export const languages: LanguageDefinition[] = [
  { code: 'as', name: 'Assamese', nativeName: 'অসমীয়া', script: 'Bengali-Assamese', direction: 'ltr', group: 'scheduled' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', script: 'Bengali', direction: 'ltr', group: 'scheduled' },
  { code: 'brx', name: 'Bodo', nativeName: 'बड़ो', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'doi', name: 'Dogri', nativeName: 'डोगरी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', script: 'Gujarati', direction: 'ltr', group: 'scheduled' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', script: 'Kannada', direction: 'ltr', group: 'scheduled' },
  { code: 'ks', name: 'Kashmiri', nativeName: 'कश्मीरी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'kok', name: 'Konkani', nativeName: 'कोंकणी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'mai', name: 'Maithili', nativeName: 'मैथिली', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', script: 'Malayalam', direction: 'ltr', group: 'scheduled' },
  { code: 'mni', name: 'Manipuri', nativeName: 'মণিপুরী / মৈতৈলোন', script: 'Meitei/Bengali', direction: 'ltr', group: 'scheduled' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'ne', name: 'Nepali', nativeName: 'नेपाली', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ', script: 'Odia', direction: 'ltr', group: 'scheduled' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', script: 'Gurmukhi', direction: 'ltr', group: 'scheduled' },
  { code: 'sa', name: 'Sanskrit', nativeName: 'संस्कृतम्', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'sat', name: 'Santali', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ', script: 'Ol Chiki', direction: 'ltr', group: 'scheduled' },
  { code: 'sd', name: 'Sindhi', nativeName: 'सिन्धी', script: 'Devanagari', direction: 'ltr', group: 'scheduled' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', script: 'Tamil', direction: 'ltr', group: 'scheduled' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', script: 'Telugu', direction: 'ltr', group: 'scheduled' },
  { code: 'ur', name: 'Urdu', nativeName: 'اردو', script: 'Arabic', direction: 'rtl', group: 'scheduled' },
  { code: 'en', name: 'English', nativeName: 'English', script: 'Latin', direction: 'ltr', group: 'extended' },
  { code: 'bho', name: 'Bhojpuri', nativeName: 'भोजपुरी', script: 'Devanagari', direction: 'ltr', group: 'extended' },
  { code: 'raj', name: 'Rajasthani', nativeName: 'राजस्थानी', script: 'Devanagari', direction: 'ltr', group: 'extended' },
  { code: 'hne', name: 'Chhattisgarhi', nativeName: 'छत्तीसगढ़ी', script: 'Devanagari', direction: 'ltr', group: 'extended' },
  { code: 'tcy', name: 'Tulu', nativeName: 'ತುಳು', script: 'Kannada', direction: 'ltr', group: 'extended' },
  { code: 'kha', name: 'Khasi', nativeName: 'কা খাসি', script: 'Bengali', direction: 'ltr', group: 'extended' },
  { code: 'lus', name: 'Mizo', nativeName: 'Mizo', script: 'Latin', direction: 'ltr', group: 'extended' },
  { code: 'grt', name: 'Garo', nativeName: 'আচিক', script: 'Bengali', direction: 'ltr', group: 'extended' },
  { code: 'trp', name: 'Kokborok', nativeName: 'ককবরক', script: 'Bengali', direction: 'ltr', group: 'extended' },
];

export const defaultLanguage = 'en';
export const findLanguage = (code: string) => languages.find(language => language.code === code);
