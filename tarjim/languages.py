from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    native: str
    rtl: bool = False
    font: str = "Segoe UI"
    line_chars: int = 42
    reading_cps: float = 17.0
    spaced: bool = True


def arabic_script(code: str, name: str, native: str) -> Language:
    return Language(code, name, native, rtl=True, font="Dubai")


def chinese(code: str, name: str, native: str, font: str) -> Language:
    return Language(code, name, native, font=font, line_chars=16, reading_cps=9.0, spaced=False)


LANGUAGES = {lang.code: lang for lang in [
    arabic_script("ar", "Arabic", "العربية"),
    Language("en", "English", "English"),
    Language("fr", "French", "Français"),
    Language("es", "Spanish", "Español"),
    Language("de", "German", "Deutsch"),
    Language("it", "Italian", "Italiano"),
    Language("pt", "Portuguese", "Português"),
    Language("nl", "Dutch", "Nederlands"),
    Language("sv", "Swedish", "Svenska"),
    Language("pl", "Polish", "Polski"),
    Language("cs", "Czech", "Čeština"),
    Language("ro", "Romanian", "Română"),
    Language("hu", "Hungarian", "Magyar"),
    Language("el", "Greek", "Ελληνικά"),
    Language("ru", "Russian", "Русский"),
    Language("uk", "Ukrainian", "Українська"),
    Language("tr", "Turkish", "Türkçe"),
    arabic_script("fa", "Persian", "فارسی"),
    arabic_script("ur", "Urdu", "اردو"),
    Language("he", "Hebrew", "עברית", rtl=True),
    Language("hi", "Hindi", "हिन्दी", font="Nirmala UI"),
    Language("bn", "Bengali", "বাংলা", font="Nirmala UI"),
    Language("ta", "Tamil", "தமிழ்", font="Nirmala UI"),
    Language("id", "Indonesian", "Bahasa Indonesia"),
    Language("ms", "Malay", "Bahasa Melayu"),
    Language("tl", "Filipino", "Filipino"),
    Language("vi", "Vietnamese", "Tiếng Việt"),
    Language("th", "Thai", "ไทย", font="Leelawadee UI", line_chars=35, reading_cps=15.0,
             spaced=False),
    Language("sw", "Swahili", "Kiswahili"),
    Language("am", "Amharic", "አማርኛ", font="Ebrima"),
    chinese("zh", "Chinese (Simplified)", "简体中文", "Microsoft YaHei"),
    chinese("zh-TW", "Chinese (Traditional)", "繁體中文", "Microsoft JhengHei"),
    Language("ja", "Japanese", "日本語", font="Yu Gothic UI", line_chars=13, reading_cps=4.0,
             spaced=False),
    Language("ko", "Korean", "한국어", font="Malgun Gothic", line_chars=16, reading_cps=12.0),
]}


def language(code: str) -> Language:
    return LANGUAGES.get(code) or Language(code, code, code)
