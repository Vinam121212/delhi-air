"""Tiny English → Hindi translation layer for the interface chrome.

Call set_lang("hi") once per run, then wrap visible strings in t("..."). Unknown strings fall back to English.
"""
_LANG = "en"

HI = {
    # sidebar
    "Live air-quality intelligence": "लाइव वायु-गुणवत्ता जानकारी",
    "Location": "स्थान", "City": "शहर", "Zone": "क्षेत्र", "Locality": "इलाका", "All zones": "सभी क्षेत्र",
    "Use my location": "मेरा स्थान इस्तेमाल करें", "Pollutants": "प्रदूषक", "Focus pollutant": "मुख्य प्रदूषक चुनें",
    "Overall AQI": "कुल AQI", "Pollutants on trend charts": "ट्रेंड चार्ट पर प्रदूषक", "AQI standard": "AQI मानक",
    "Health profile": "स्वास्थ्य प्रोफ़ाइल", "Live updates": "लाइव अपडेट", "Auto-refresh": "अपने-आप रीफ़्रेश",
    "Refresh every": "हर इतने में रीफ़्रेश", "Animated sky": "एनिमेटेड आसमान", "⟳  Refresh now": "⟳  अभी रीफ़्रेश करें",
    "Alerts": "अलर्ट", "AQI alerts": "AQI अलर्ट", "Alert me when AQI reaches": "जब AQI यहाँ पहुँचे तब बताएँ",
    "Also warn about the next 3 hours": "अगले 3 घंटों के बारे में भी चेतावनी दें", "Language": "भाषा",
    "Live station data (optional)": "लाइव स्टेशन डेटा (वैकल्पिक)",
    "Live station data is on for everyone": "सभी के लिए लाइव स्टेशन डेटा चालू है", "Measured at": "यहाँ मापा गया",
    # views & tabs
    "🌍 Live": "🌍 लाइव", "📊 Weekly": "📊 साप्ताहिक", "Weekly report": "साप्ताहिक रिपोर्ट", "⚖️ Compare": "⚖️ तुलना", "🫁 My exposure": "🫁 मेरा एक्सपोज़र", "📅 History": "📅 इतिहास",
    "📚 Learn": "📚 जानें", "📈 Trends": "📈 ट्रेंड", "🔮 Forecast": "🔮 पूर्वानुमान", "🗓️ Planner": "🗓️ प्लानर",
    "🔎 Why?": "🔎 क्यों?", "🗺️ Map": "🗺️ नक्शा", "🏙️ Compare areas": "🏙️ इलाकों की तुलना", "❤️ Health advice": "❤️ स्वास्थ्य सलाह",
    # hero / home
    "LIVE · updates every": "लाइव · हर", "min": "मिनट", "AUTO-REFRESH PAUSED": "ऑटो-रीफ़्रेश रुका है",
    "Reading for": "रीडिंग", "checked": "जाँचा", "Hourly forecast": "घंटेवार पूर्वानुमान", "Now": "अभी",
    "day AQI forecast": "दिन का AQI पूर्वानुमान", "Today": "आज", "Main pollutant": "मुख्य प्रदूषक",
    "Cigarette equivalent": "सिगरेट के बराबर", "Since yesterday": "कल से", "Wind": "हवा", "Humidity": "नमी",
    "Visibility": "दृश्यता", "AQI scale": "AQI पैमाना",
    "Bars show each day's low → high AQI. White dot = now.": "बार हर दिन का न्यूनतम → अधिकतम AQI दिखाते हैं। सफ़ेद बिंदु = अभी।",
    "Tap any box for details": "विवरण के लिए किसी भी बॉक्स पर टैप करें",
    # categories
    "Good": "अच्छा", "Satisfactory": "संतोषजनक", "Moderate": "मध्यम", "Poor": "खराब", "Very Poor": "बहुत खराब",
    "Severe": "गंभीर", "Unhealthy for Sensitive Groups": "संवेदनशील लोगों के लिए अस्वस्थ", "Unhealthy": "अस्वस्थ",
    "Very Unhealthy": "बहुत अस्वस्थ", "Hazardous": "खतरनाक",
    # planner / compare / exposure / causes
    "Plan the cleanest time to go outside": "बाहर जाने का सबसे साफ़ समय चुनें", "Activity": "गतिविधि",
    "Duration": "अवधि", "When": "कब", "Earliest / latest hour": "सबसे जल्दी / सबसे देर का समय",
    "Best slots": "सबसे अच्छे समय", "Why is the air like this?": "हवा ऐसी क्यों है?",
    "Compare two places": "दो जगहों की तुलना", "Place A": "जगह A", "Place B": "जगह B",
    "Your daily clean-air score": "आपका दैनिक स्वच्छ-हवा स्कोर", "Log time outdoors": "बाहर बिताया समय दर्ज करें",
    "Add": "जोड़ें", "Streak": "लगातार दिन",
}


def set_lang(lang: str):
    global _LANG
    _LANG = "hi" if lang.startswith("हि") or lang == "hi" else "en"


def lang() -> str:
    return _LANG


def t(s: str) -> str:
    return HI.get(s, s) if _LANG == "hi" else s
