"""自动验证模块。"""

from .detector import VerificationPlan, detect_verification
from .result import VerificationResult
from .verifier import Verifier

__all__ = [
    "VerificationPlan",
    "VerificationResult",
    "Verifier",
    "detect_verification",
]
