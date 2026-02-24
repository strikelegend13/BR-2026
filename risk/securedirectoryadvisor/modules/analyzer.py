"""
analyzer.py - Core file and URL risk analysis logic
Uses plain-English, friendly messaging suitable for elderly/non-technical users.
Optionally integrates with VirusTotal and Google Safe Browsing APIs.
"""

import hashlib
import ipaddress
import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------
RISK_SAFE = "safe"
RISK_CAUTION = "caution"
RISK_DANGER = "danger"

_RISK_ORDER = [RISK_SAFE, RISK_CAUTION, RISK_DANGER]


def _higher_risk(current: str, new: str) -> str:
    """Return whichever risk level is more severe."""
    if _RISK_ORDER.index(new) > _RISK_ORDER.index(current):
        return new
    return current


def _invalid_url_result(raw_url: str) -> dict:
    return {
        "type": "url",
        "url": raw_url,
        "overall_risk": RISK_CAUTION,
        "findings": [{
            "risk": RISK_CAUTION,
            "title": "⚠️ We couldn't understand this web address",
            "detail": f"The address '{raw_url}' doesn't look like a normal web address. Please double-check it.",
        }],
        "scanned_at": datetime.now().isoformat(),
    }


def _is_valid_hostname(hostname: str) -> bool:
    """Basic host validation for user-entered URLs."""
    if not hostname:
        return False
    if len(hostname) > 253:
        return False
    if any(ch.isspace() for ch in hostname):
        return False

    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        pass

    normalized = hostname[:-1] if hostname.endswith(".") else hostname
    labels = normalized.split(".")
    if any(not label for label in labels):
        return False

    for label in labels:
        if len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(ch.isalnum() or ch == "-" for ch in label):
            return False
    return True


def _is_plausible_web_url(url: str, parsed: urllib.parse.ParseResult) -> bool:
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    if any(ch.isspace() for ch in url):
        return False
    if not _is_valid_hostname(parsed.hostname or ""):
        return False
    try:
        parsed.port
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# Extension lists
# ---------------------------------------------------------------------------
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.ps1', '.vbs', '.msi', '.jar',
    '.scr', '.lnk', '.hta', '.pif', '.com', '.reg', '.wsf',
    '.cpl', '.msc', '.msp', '.gadget', '.application'
}

SCRIPT_EXTENSIONS = {
    '.js', '.jse', '.vbe', '.wsh', '.wsc', '.sh', '.bash',
    '.zsh', '.fish', '.py', '.rb', '.pl', '.php'
}

DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.csv'
}

MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
}

ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz',
}

SUSPICIOUS_KEYWORDS = [
    'invoice', 'payment', 'urgent', 'update', 'tracking',
    'details', 'confirmation', 'receipt', 'refund', 'verify',
    'account', 'suspended', 'click', 'free', 'prize', 'winner',
    'bank', 'password', 'credential', 'login'
]

SCAM_URL_KEYWORDS = [
    'free', 'winner', 'prize', 'claim', 'urgent', 'verify',
    'suspended', 'confirm', 'unusual', 'limited', 'act-now',
    'click-here', 'login-required', 'update-required'
]

TRUSTED_DOMAINS = {
    'google.com', 'youtube.com', 'microsoft.com', 'apple.com',
    'amazon.com', 'bbc.com', 'bbc.co.uk', 'nhs.uk', 'gov.uk',
    'usa.gov', 'irs.gov', 'medicare.gov', 'wikipedia.org',
    'facebook.com', 'gmail.com', 'outlook.com', 'yahoo.com'
}

# ---------------------------------------------------------------------------
# Friendly message templates
# ---------------------------------------------------------------------------
MESSAGES = {
    "double_extension": (
        RISK_DANGER,
        "🛑 This file is trying to trick you!",
        "The file '{name}' is pretending to be a '{fake_ext}' file, but it's actually "
        "a program that could run on your computer. This is a very common trick used by "
        "scammers. Please do NOT open this file. If someone sent it to you, do not reply "
        "— contact a family member or friend for help."
    ),
    "dangerous_extension": (
        RISK_DANGER,
        "🛑 This file could be dangerous",
        "The file '{name}' is a type of program (ending in '{ext}'). Programs can make "
        "changes to your computer — sometimes harmful ones. Unless you were specifically "
        "expecting to install something, it's safest not to open this. Ask a trusted "
        "person before continuing."
    ),
    "script_extension": (
        RISK_DANGER,
        "🛑 This is a script file — be careful",
        "The file '{name}' is a script (ending in '{ext}'). Scripts are like mini-programs "
        "and can change things on your computer. If you didn't ask for this, don't open it. "
        "Ask someone you trust to take a look first."
    ),
    "suspicious_name_danger": (
        RISK_DANGER,
        "⚠️ This looks like it could be a scam file",
        "The file is named '{name}' and uses the word '{keyword}' — scammers often use "
        "urgent-sounding words like this to trick people into opening dangerous files. "
        "Be very cautious."
    ),
    "document_with_macro_risk": (
        RISK_CAUTION,
        "⚠️ This is a document — just double-check before opening",
        "The file '{name}' looks like a normal document, which is usually fine. However, "
        "documents can sometimes contain hidden programs called 'macros'. If your computer "
        "asks you to 'Enable Macros' or 'Enable Content' after opening it — say NO and "
        "close the file. When in doubt, ask a family member."
    ),
    "archive_file": (
        RISK_CAUTION,
        "⚠️ This is a compressed archive — check what's inside",
        "The file '{name}' is a compressed archive (like a folder of files). Archives can "
        "contain anything, including dangerous programs. Don't open files inside it unless "
        "you trust whoever sent it. Ask a family member if you're unsure."
    ),
    "media_or_safe": (
        RISK_SAFE,
        "✅ This file looks safe",
        "The file '{name}' appears to be a {type_description}. This type of file is "
        "generally safe to open. Still, only open files from people or websites you trust."
    ),
    "unknown_extension": (
        RISK_CAUTION,
        "⚠️ We're not sure about this file",
        "The file '{name}' has an unusual type ('{ext}') that we don't recognise. "
        "It might be perfectly fine, but if you weren't expecting it, it's worth asking "
        "someone you trust before opening it."
    ),
    "empty_file": (
        RISK_CAUTION,
        "⚠️ This file appears to be empty",
        "The file '{name}' contains no data at all. An empty file is unusual and may "
        "mean the download didn't finish properly, or that something went wrong. "
        "You can safely delete it and try downloading again if you need it."
    ),
    "suspicious_name_caution": (
        RISK_CAUTION,
        "⚠️ This file has an attention-grabbing name — double-check before opening",
        "The file is named '{name}' and uses the word '{keyword}'. Scammers often use "
        "urgent or exciting words like this to trick people into opening files. If you "
        "weren't expecting this file, it's worth asking someone you trust before opening it."
    ),
    "virustotal_clean": (
        RISK_SAFE,
        "✅ Checked with security services — looks clean",
        "We checked this file against online security databases and no threats were found. "
        "That's a good sign, though it's still best to only open files you were expecting."
    ),
    "virustotal_detected": (
        RISK_DANGER,
        "🛑 Security services flagged this file!",
        "We checked this file against online security databases and {count} security "
        "service(s) flagged it as potentially harmful. Do NOT open this file. "
        "You should delete it and let a trusted person know."
    ),
}

URL_MESSAGES = {
    "trusted_domain": (
        RISK_SAFE,
        "✅ This looks like a well-known, trusted website",
        "The address '{url}' appears to belong to a well-known and trusted website. "
        "It should be safe to visit, but always make sure the spelling is exactly right — "
        "scammers sometimes use addresses that look almost right (like 'arnazon.com' instead of 'amazon.com')."
    ),
    "suspicious_keywords": (
        RISK_DANGER,
        "🛑 This website looks suspicious",
        "The address '{url}' contains words often used in scam or phishing websites. "
        "We strongly suggest you do NOT visit this site. If a message or email told you "
        "to go there, it could be a scam. Ask a family member or friend for help."
    ),
    "non_https": (
        RISK_CAUTION,
        "⚠️ This website may not be secure",
        "The address '{url}' doesn't use a secure connection (it starts with 'http' rather "
        "than 'https'). Avoid entering any personal details, passwords, or payment "
        "information on this site."
    ),
    "long_or_odd_url": (
        RISK_CAUTION,
        "⚠️ This web address looks unusual",
        "The address '{url}' looks more complicated than normal websites. Legitimate "
        "websites usually have short, simple addresses. Be cautious and check with "
        "someone you trust before visiting."
    ),
    "safe_url": (
        RISK_SAFE,
        "✅ This web address looks okay",
        "The address '{url}' doesn't show obvious warning signs. It should be fine to "
        "visit, but always be careful about entering personal information on any website."
    ),
    "google_flagged": (
        RISK_DANGER,
        "🛑 WARNING: This site has been reported as dangerous!",
        "The address '{url}' has been flagged by Google's safety services as a harmful "
        "or deceptive website. Do NOT visit this site. If someone sent you this link, "
        "do not reply to them — it may be a scam."
    ),
    "lookalike_domain": (
        RISK_DANGER,
        "🛑 This website is imitating a well-known site!",
        "The address '{url}' looks very similar to '{real_domain}' but the spelling is "
        "slightly different. This is a very common trick used by scammers to steal your "
        "personal information. Do NOT visit this site or enter any details."
    ),
    "ip_address_url": (
        RISK_CAUTION,
        "⚠️ This web address uses a raw number instead of a name",
        "The address '{url}' uses a numeric IP address instead of a normal website name. "
        "Legitimate websites almost never ask you to visit an address like this. This "
        "could be a trick. Unless you know exactly what this is, do not visit it."
    ),
}

# ---------------------------------------------------------------------------
# Lookalike / homoglyph domain detection
# ---------------------------------------------------------------------------
_HOMOGLYPH_MAP = str.maketrans({
    "0": "o", "1": "l", "!": "l", "|": "l",
    "5": "s", "8": "b", "@": "a", "$": "s",
    "3": "e",
})

_LOOKALIKE_TARGETS = {
    "google": "google.com",
    "youtube": "youtube.com",
    "microsoft": "microsoft.com",
    "apple": "apple.com",
    "amazon": "amazon.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "paypal": "paypal.com",
    "netflix": "netflix.com",
    "ebay": "ebay.com",
    "yahoo": "yahoo.com",
    "outlook": "outlook.com",
    "gmail": "gmail.com",
    "wikipedia": "wikipedia.org",
}


def _check_lookalike(base_domain: str) -> str | None:
    """Return the real domain if *base_domain* looks like a misspelling of a
    well-known site, otherwise None."""
    if any(base_domain == td or base_domain.endswith("." + td)
           for td in TRUSTED_DOMAINS):
        return None

    normalized = base_domain.split(".")[0].lower().translate(_HOMOGLYPH_MAP)

    for brand, real_domain in _LOOKALIKE_TARGETS.items():
        if normalized == brand:
            return None
        dist = _levenshtein(normalized, brand)
        if 0 < dist <= 2 and len(normalized) >= 4:
            return real_domain
    return None


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if ca == cb else 1),
            ))
        prev = curr
    return prev[-1]


# ---------------------------------------------------------------------------
# File size helper
# ---------------------------------------------------------------------------
def format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    for unit in ("KB", "MB", "GB"):
        size_bytes /= 1024.0
        if size_bytes < 1024.0 or unit == "GB":
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} GB"


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------
def hash_file(filepath: str) -> str | None:
    try:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except OSError as exc:
        log.warning("Could not hash file %s: %s", filepath, exc)
        return None


# ---------------------------------------------------------------------------
# File analysis
# ---------------------------------------------------------------------------
def analyze_file(filepath: str, vt_api_key: str = "") -> dict:
    filename = os.path.basename(filepath)
    name_lower = filename.lower()
    root, ext = os.path.splitext(name_lower)
    ext = ext.lower()

    findings = []
    overall_risk = RISK_SAFE
    file_hash = hash_file(filepath)

    try:
        file_size_bytes = os.path.getsize(filepath)
    except OSError:
        file_size_bytes = -1

    # 0. Empty-file check
    try:
        if file_size_bytes == 0:
            tpl = MESSAGES["empty_file"]
            findings.append({
                "risk": tpl[0],
                "title": tpl[1],
                "detail": tpl[2].format(name=filename)
            })
            overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
    except OSError:
        pass

    # 1. Double extension check
    if '.' in root and ext in DANGEROUS_EXTENSIONS:
        fake_ext = '.' + root.rsplit('.', 1)[-1]
        tpl = MESSAGES["double_extension"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, fake_ext=fake_ext, ext=ext)
        })
        overall_risk = _higher_risk(overall_risk, RISK_DANGER)

    # 2. Extension risk
    if ext in DANGEROUS_EXTENSIONS:
        tpl = MESSAGES["dangerous_extension"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, ext=ext)
        })
        overall_risk = _higher_risk(overall_risk, RISK_DANGER)
    elif ext in SCRIPT_EXTENSIONS:
        tpl = MESSAGES["script_extension"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, ext=ext)
        })
        overall_risk = _higher_risk(overall_risk, RISK_DANGER)
    elif ext in DOCUMENT_EXTENSIONS:
        tpl = MESSAGES["document_with_macro_risk"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, ext=ext)
        })
        overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
    elif ext in ARCHIVE_EXTENSIONS:
        tpl = MESSAGES["archive_file"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename)
        })
        overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
    elif ext in MEDIA_EXTENSIONS:
        type_map = {
            **{e: "photo or image" for e in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']},
            **{e: "music or audio file" for e in ['.mp3', '.wav']},
            **{e: "video file" for e in ['.mp4', '.avi', '.mov', '.mkv']},
        }
        type_desc = type_map.get(ext, "media file")
        tpl = MESSAGES["media_or_safe"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, type_description=type_desc)
        })
    else:
        tpl = MESSAGES["unknown_extension"]
        findings.append({
            "risk": tpl[0],
            "title": tpl[1],
            "detail": tpl[2].format(name=filename, ext=ext if ext else "(none)")
        })
        overall_risk = _higher_risk(overall_risk, RISK_CAUTION)

    # 3. Suspicious keyword check
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in name_lower:
            if ext in DANGEROUS_EXTENSIONS or ext in SCRIPT_EXTENSIONS:
                tpl = MESSAGES["suspicious_name_danger"]
                findings.append({
                    "risk": tpl[0],
                    "title": tpl[1],
                    "detail": tpl[2].format(name=filename, keyword=kw)
                })
                overall_risk = _higher_risk(overall_risk, RISK_DANGER)
            elif ext in DOCUMENT_EXTENSIONS or ext in ARCHIVE_EXTENSIONS:
                tpl = MESSAGES["suspicious_name_caution"]
                findings.append({
                    "risk": tpl[0],
                    "title": tpl[1],
                    "detail": tpl[2].format(name=filename, keyword=kw)
                })
                overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
            break

    # 4. VirusTotal check (if API key provided and hash available)
    if vt_api_key and file_hash:
        vt_result = check_virustotal_hash(file_hash, vt_api_key)
        if vt_result is not None:
            if vt_result == 0:
                tpl = MESSAGES["virustotal_clean"]
                findings.append({
                    "risk": tpl[0],
                    "title": tpl[1],
                    "detail": tpl[2]
                })
            elif vt_result > 0:
                tpl = MESSAGES["virustotal_detected"]
                findings.append({
                    "risk": tpl[0],
                    "title": tpl[1],
                    "detail": tpl[2].format(count=vt_result)
                })
                overall_risk = _higher_risk(overall_risk, RISK_DANGER)

    return {
        "type": "file",
        "filename": filename,
        "filepath": filepath,
        "file_hash": file_hash,
        "file_size_bytes": file_size_bytes,
        "file_size": format_file_size(file_size_bytes) if file_size_bytes >= 0 else "unknown",
        "ext": ext,
        "overall_risk": overall_risk,
        "findings": findings,
        "scanned_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# URL analysis
# ---------------------------------------------------------------------------
def analyze_url(raw_url: str, gsb_api_key: str = "") -> dict:
    url = raw_url.strip()
    if not url:
        return _invalid_url_result(raw_url)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    findings = []
    overall_risk = RISK_SAFE

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return _invalid_url_result(raw_url)

    if not _is_plausible_web_url(url, parsed):
        return _invalid_url_result(raw_url)

    domain = parsed.netloc.lower()
    base_domain = domain.removeprefix("www.")
    full_lower = url.lower()

    # 1. Google Safe Browsing
    if gsb_api_key:
        flagged = check_google_safe_browsing(url, gsb_api_key)
        if flagged:
            tpl = URL_MESSAGES["google_flagged"]
            findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
            overall_risk = _higher_risk(overall_risk, RISK_DANGER)

    # 2. Lookalike domain check
    lookalike_match = _check_lookalike(base_domain)
    if lookalike_match:
        tpl = URL_MESSAGES["lookalike_domain"]
        findings.append({"risk": tpl[0], "title": tpl[1],
                         "detail": tpl[2].format(url=url, real_domain=lookalike_match)})
        overall_risk = _higher_risk(overall_risk, RISK_DANGER)

    # 3. IP address URL check
    hostname = parsed.hostname or ""
    try:
        ipaddress.ip_address(hostname)
        is_ip_url = True
    except ValueError:
        is_ip_url = False
    if is_ip_url:
        tpl = URL_MESSAGES["ip_address_url"]
        findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
        overall_risk = _higher_risk(overall_risk, RISK_CAUTION)

    # 4. Trusted domain check
    is_trusted = any(base_domain == td or base_domain.endswith("." + td) for td in TRUSTED_DOMAINS)

    # 5. Suspicious keywords
    has_suspicious_kw = any(kw in full_lower for kw in SCAM_URL_KEYWORDS)

    # 6. HTTPS check
    is_https = parsed.scheme == "https"

    # 7. Unusual URL structure
    is_long_or_odd = len(url) > 100 or url.count(".") > 4 or "@" in url

    if is_trusted and is_https and not has_suspicious_kw:
        tpl = URL_MESSAGES["trusted_domain"]
        findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
    elif has_suspicious_kw and not is_trusted:
        tpl = URL_MESSAGES["suspicious_keywords"]
        findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
        overall_risk = _higher_risk(overall_risk, RISK_DANGER)
    else:
        if not is_https:
            tpl = URL_MESSAGES["non_https"]
            findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
            overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
        if is_long_or_odd:
            tpl = URL_MESSAGES["long_or_odd_url"]
            findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})
            overall_risk = _higher_risk(overall_risk, RISK_CAUTION)
        if not findings:
            tpl = URL_MESSAGES["safe_url"]
            findings.append({"risk": tpl[0], "title": tpl[1], "detail": tpl[2].format(url=url)})

    return {
        "type": "url",
        "url": raw_url,
        "overall_risk": overall_risk,
        "findings": findings,
        "scanned_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# VirusTotal API
# ---------------------------------------------------------------------------
def check_virustotal_hash(file_hash: str, api_key: str) -> int | None:
    """Returns number of detections, or None if unavailable."""
    try:
        req = urllib.request.Request(
            f"https://www.virustotal.com/api/v3/files/{file_hash}",
            headers={"x-apikey": api_key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            stats = data["data"]["attributes"]["last_analysis_stats"]
            return stats.get("malicious", 0) + stats.get("suspicious", 0)
    except Exception as exc:
        log.info("VirusTotal lookup failed for %s: %s", file_hash[:12], exc)
        return None


# ---------------------------------------------------------------------------
# Google Safe Browsing API
# ---------------------------------------------------------------------------
def check_google_safe_browsing(url: str, api_key: str) -> bool:
    """Returns True if URL is flagged as dangerous."""
    try:
        payload = json.dumps({
            "client": {"clientId": "SecureFileAdvisor", "clientVersion": "2.0"},
            "threatInfo": {
                "threatTypes": [
                    "MALWARE", "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }).encode()
        req = urllib.request.Request(
            f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return bool(data.get("matches"))
    except Exception as exc:
        log.info("Google Safe Browsing lookup failed for %s: %s", url, exc)
        return False
