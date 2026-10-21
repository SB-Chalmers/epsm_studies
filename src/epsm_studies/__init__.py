"""Named research protocols; reusable search/execution lives in epsm_workflows."""

import logging as _stdlib_logging

from .study import PaperStudy
from .spec import StudySpec
from .facade import Study
from .comparison import compare_energy_results, write_comparison_report

__version__ = "0.3.0"
__all__ = ["Study", "StudySpec", "PaperStudy", "compare_energy_results", "write_comparison_report"]

# A library emits no output until its host selects handlers.

_stdlib_logging.getLogger("epsm_studies").addHandler(_stdlib_logging.NullHandler())
