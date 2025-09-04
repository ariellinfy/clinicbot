
import re
from typing import Tuple, List
import logging
import hanzidentifier

logger = logging.getLogger(__name__)

class PIIRedactor:
    def __init__(self):
        self.patterns = {
            'phone': {
                'en': [r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'],
                'zh': [
                    r'(?<!\d)(?:\+?86[-.\s]?)?1[3-9]\d{9}(?!\d)',
                    r'(?<!\d)(?:\+?886[-.\s]?)?09\d{8}(?!\d)',
                    r'(?<!\d)(?:\+?852[-.\s]?)?[569]\d{7}(?!\d)'
                ]
            },
            'email': [r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'],
            'id_numbers': {
                'en': [r'\d{3}[-.\s]?\d{2}[-.\s]?\d{4}'],
                'zh': [
                    r'[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[012])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]',
                    r'[A-Z]\d{9}'
                ]
            },
            'names': {
                'en': [
                    r'\bmy name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',
                    r'\bi am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',
                    r"\bi'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
                ],
                'zh-Hans': [r'我叫([\u4e00-\u9fff]{2,4})', r'我是([\u4e00-\u9fff]{2,4})', r'我的名字是([\u4e00-\u9fff]{2,4})'],
                'zh-Hant': [r'我叫([\u4e00-\u9fff]{2,4})', r'我是([\u4e00-\u9fff]{2,4})', r'我的名字是([\u4e00-\u9fff]{2,4})']
            },
            'address': {
                'en': [r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)'],
                'zh': [
                    r'[\u4e00-\u9fff]+[市区縣县][\u4e00-\u9fff]+[路街道巷弄]\d*号?',
                    r'[\u4e00-\u9fff]+省[\u4e00-\u9fff]+市'
                ]
            },
            'dates': [r'(19|20)\d{2}[-/年](0?[1-9]|1[0-2])[-/月](0?[1-9]|[12][0-9]|3[01])日?']
        }
        self._compile_patterns()
        self.replacements = {
            'phone': '[PHONE_REDACTED]',
            'email': '[EMAIL_REDACTED]',
            'id_numbers': '[ID_REDACTED]',
            'names': '[NAME_REDACTED]',
            'address': '[ADDRESS_REDACTED]',
            'dates': '[DATE_REDACTED]'
        }

    def _compile_patterns(self):
        self.compiled_patterns = {}
        for category, patterns in self.patterns.items():
            if isinstance(patterns, dict):
                self.compiled_patterns[category] = {}
                for lang, lang_patterns in patterns.items():
                    self.compiled_patterns[category][lang] = [re.compile(p, re.IGNORECASE) for p in lang_patterns]
            else:
                self.compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def redact_pii(self, text: str, language: str = 'en') -> Tuple[str, List[str]]:
        if not text:
            return text, []
        redacted_text = text
        redaction_log = []
        try:
            # emails
            for pattern in self.compiled_patterns['email']:
                matches = list(pattern.finditer(redacted_text))
                if matches:
                    redacted_text = pattern.sub(self.replacements['email'], redacted_text)
                    redaction_log += ["email"] * len(matches)
            # ids
            patterns = self.compiled_patterns['id_numbers']['zh'] if language.startswith('zh') else self.compiled_patterns['id_numbers']['en']
            for pattern in patterns:
                for m in list(pattern.finditer(redacted_text)):
                    redacted_text = redacted_text.replace(m.group(0), self.replacements['id_numbers'])
                    redaction_log.append("id")
            # phones
            patterns = self.compiled_patterns['phone']['zh'] if language.startswith('zh') else self.compiled_patterns['phone']['en']
            for pattern in patterns:
                matches = list(pattern.finditer(redacted_text))
                if matches:
                    redacted_text = pattern.sub(self.replacements['phone'], redacted_text)
                    redaction_log += ["phone"] * len(matches)
            # names
            if language in self.compiled_patterns['names']:
                for pattern in self.compiled_patterns['names'][language]:
                    for m in list(pattern.finditer(redacted_text)):
                        name = m.group(1)
                        redacted_text = redacted_text.replace(name, self.replacements['names'])
                        redaction_log.append("name")
            # addresses
            patterns = self.compiled_patterns['address']['zh'] if language.startswith('zh') else self.compiled_patterns['address']['en']
            for pattern in patterns:
                for m in list(pattern.finditer(redacted_text)):
                    redacted_text = redacted_text.replace(m.group(0), self.replacements['address'])
                    redaction_log.append("address")
            # dates
            for pattern in self.compiled_patterns['dates']:
                for m in list(pattern.finditer(redacted_text)):
                    redacted_text = redacted_text.replace(m.group(0), self.replacements['dates'])
                    redaction_log.append("date")
        except Exception as e:
            logger.warning(f"PII redaction error: {e}")
            return text, []
        return redacted_text, redaction_log

def detect_language(text: str) -> str:
    if not text:
        return "en"
    if not hanzidentifier.has_chinese(text):
        return "en"
    if hanzidentifier.is_traditional(text):
        return "zh-Hant"
    if hanzidentifier.is_simplified(text):
        return "zh-Hans"
    return "en"

_redactor = PIIRedactor()

def sanitize_text_for_llm(text: str, lang: str):
    if not text: 
        return "", []
    red, log = _redactor.redact_pii(text, lang)
    red = re.sub(r'\\b\\d{4,}\\b', '[NUMBER_REDACTED]', red)
    red = re.sub(r'@\\w+', '[HANDLE_REDACTED]', red)
    return red, log

def redact_text_before_return(text: str, lang: str) -> str:
    red, _ = _redactor.redact_pii(text, lang)
    red = re.sub(r'\\b\\d{4,}\\b', '[NUMBER_REDACTED]', red)
    red = re.sub(r'@\\w+', '[HANDLE_REDACTED]', red)
    return red
