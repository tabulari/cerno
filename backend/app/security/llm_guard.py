from llm_guard import scan_prompt, scan_output
from llm_guard.input_scanners import PromptInjection, Toxicity, InvisibleText
from llm_guard.output_scanners import Sensitive
from fastapi import HTTPException, status
import structlog

logger = structlog.get_logger()

_input_scanners = None
_output_scanners = None

def _get_input_scanners():
    global _input_scanners
    if _input_scanners is None:
        _input_scanners = [
            PromptInjection(threshold=0.5),
            Toxicity(threshold=0.5),
            InvisibleText(),
        ]
    return _input_scanners

def _get_output_scanners():
    global _output_scanners
    if _output_scanners is None:
        _output_scanners = [
            Sensitive()
        ]
    return _output_scanners

def scan_input(prompt: str) -> str:
    """Scans input prompt for injections and toxicity."""
    if not prompt:
        return prompt
    
    try:
        sanitized_prompt, results_valid, results_score = scan_prompt(_get_input_scanners(), prompt)
        if any(not is_valid for is_valid in results_valid.values()):
            failed_scanners = [scanner for scanner, is_valid in results_valid.items() if not is_valid]
            logger.warning("security.llm_guard.input_blocked", scanners=failed_scanners)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security violation detected by LLM-Guard: {', '.join(failed_scanners)}"
            )
        return sanitized_prompt
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("security.llm_guard.input_scan_error", error=str(e))
        return prompt

def scan_llm_output(prompt: str, output: str) -> str:
    """Scans LLM output for sensitive information leaks."""
    if not output:
        return output
        
    try:
        sanitized_output, results_valid, results_score = scan_output(_get_output_scanners(), prompt, output)
        if any(not is_valid for is_valid in results_valid.values()):
            failed_scanners = [scanner for scanner, is_valid in results_valid.items() if not is_valid]
            logger.warning("security.llm_guard.output_blocked", scanners=failed_scanners)
            # We don't raise here usually, we just return the sanitized output or a safe message
            return "Output redacted due to security policy violation."
        return sanitized_output
    except Exception as e:
        logger.warning("security.llm_guard.output_scan_error", error=str(e))
        return output
