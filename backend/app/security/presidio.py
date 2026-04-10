import structlog
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

logger = structlog.get_logger()

_analyzer = None
_anonymizer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer

def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

def redact_pii(text: str) -> str:
    """Redacts PII from text using Presidio."""
    if not text:
        return text
    try:
        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()
        
        results = analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", "PERSON"], language='en')
        anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized_result.text
    except Exception as e:
        logger.warning("security.presidio.failed", error=str(e))
        return text  # Fallback to original text on error
