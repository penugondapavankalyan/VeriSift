import os
from typing import Any, Dict, Optional, Tuple

from .config import VerisiftConfig
from .core import Comparator
from .models import ComparisonReport
from .pipeline.report import generate_html_report
from .utils.config_manager import ConfigManager
from .utils.health import run_health_check


CONFIG_KEY_MAPPING: Dict[str, str] = {
    "mode": "comparison_mode",
    "enable_visual": "enable_visual",
    "dpi": "dpi",
    "outputdir": "output_dir",
    "reportname": "report_name",
    "popplerpath": "poppler_path",
    "text_weightage": "txt_weightage",
    "text_threshold": "text_threshold",
    "visual_threshold": "visual_threshold",
    "semantic_threshold": "semantic_threshold",
    "semantic_max_phrase": "semantic_max_phrase",
    "enable_exclusions": "ignore_patterns_flag",
    "exclusion_patterns": "ignore_patterns",
}

def _translate_config_key(key: str) -> str:

    """
    Reverse lookup: given a VerisiftConfig attribute name, return the CLI-style key.
    """
    for cli_key, config_attr in CONFIG_KEY_MAPPING.items():
        if config_attr == key:
            return cli_key
    return key


def _normalize_config_key(key: str) -> str:
    """
    Accept CLI-style config names and normalize them to VerisiftConfig attribute names.
    """
    return CONFIG_KEY_MAPPING.get(key, key)


def validate_float_0_to_1(value: Any) -> float:
    parsed = float(value)
    if 0.0 <= parsed <= 1.0:
        return parsed
    raise ValueError("Value must be between 0.0 and 1.0 inclusive.")


def validate_int_1_to_100(value: Any) -> int:
    parsed = int(value)
    if 1 <= parsed <= 100:
        return parsed
    raise ValueError("Value must be between 1 and 100 inclusive.")


def validate_int_50_to_300(value: Any) -> int:
    parsed = int(value)
    if 50 <= parsed <= 300:
        return parsed
    raise ValueError("Value must be between 50 and 300 inclusive.")


def _validate_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in ("true", "false"):
            return lowered == "true"
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean value.")


def _validate_config_value(key: str, value: Any) -> Any:
    """
    Validate and normalize config values using the same restrictions as the CLI.
    """
    normalized_key = _normalize_config_key(key)

    if normalized_key == "comparison_mode":
        if value not in ("literal", "semantic"):
            raise ValueError("mode must be either 'literal' or 'semantic'.")
        return value

    if normalized_key == "enable_visual":
        return _validate_bool(value, "enable_visual")

    if normalized_key == "dpi":
        return validate_int_50_to_300(value)

    if normalized_key in ("txt_weightage", "text_threshold", "visual_threshold", "semantic_threshold"):
        return validate_float_0_to_1(value)

    if normalized_key == "semantic_max_phrase":
        return validate_int_1_to_100(value)

    if normalized_key == "ignore_patterns_flag":
        return _validate_bool(value, "enable_exclusions")

    if normalized_key == "ignore_patterns":
        if not isinstance(value, list):
            raise ValueError("exclusion_patterns must be a list.")
        return value

    if normalized_key in ("output_dir", "report_name", "poppler_path"):
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string.")
        return value

    if not hasattr(VerisiftConfig(), normalized_key):
        raise ValueError(f"Unknown configuration key: {key}")

    return value


def create_config(**kwargs) -> VerisiftConfig:
    """
    Create a VerisiftConfig using CLI-style parameter names.
    
    Accepts both CLI-style names (mode, outputdir, enable_exclusions) and
    internal names (comparison_mode, output_dir, ignore_patterns_flag).
    
    Args:
        **kwargs: Configuration parameters using either CLI-style or internal names.
    
    Returns:
        VerisiftConfig: Configured instance with validated parameters.
    
    Example:
        >>> config = create_config(
        ...     mode="semantic",
        ...     outputdir="./reports",
        ...     text_weightage=0.7,
        ...     enable_exclusions=True
        ... )
    
    Raises:
        ValueError: If parameter name is unknown or value is invalid.
    """
    config = VerisiftConfig()
    
    for key, value in kwargs.items():
        # Normalize CLI names to internal attribute names
        normalized_key = _normalize_config_key(key)
        
        # Validate the value
        validated_value = _validate_config_value(key, value)
        
        # Set the attribute
        if hasattr(config, normalized_key):
            setattr(config, normalized_key, validated_value)
        else:
            raise ValueError(f"Unknown configuration parameter: {key}")
    
    return config


def load_config() -> VerisiftConfig:
    """
    Load the effective configuration by merging saved user settings with defaults.
    """
    cfg_mgr = ConfigManager()
    return cfg_mgr.load_user_config()


def display_config() -> Dict[str, Any]:
    """
    Return the current effective configuration as a plain dictionary.

    Uses CLI-style keys from CONFIG_KEY_MAPPING for display.

    """

    config: VerisiftConfig = load_config()
    config_dict: dict[str, Any] = vars(config)

    

    # Map internal attribute names to CLI-style keys for display
    display_dict: dict[Any, Any] = {}
    for config_attr, value in config_dict.items():
        cli_key: str = _translate_config_key(config_attr)
        display_dict[cli_key] = value
    
    return display_dict



def set_config(key: str, value: Any) -> None:
    """
    Persist a single configuration value for future runs.

    Accepts either CLI-style names (for example: outputdir, reportname, mode)
    or internal VerisiftConfig attribute names.
    """
    cfg_mgr = ConfigManager()
    normalized_key = _normalize_config_key(key)
    validated_value = _validate_config_value(key, value)
    cfg_mgr.set_config(normalized_key, validated_value)


def set_configs(**kwargs: Any) -> Dict[str, Any]:
    """
    Persist multiple configuration values and return the updated effective config.

    Accepts either CLI-style keys or internal VerisiftConfig attribute names.
    """
    cfg_mgr = ConfigManager()
    for key, value in kwargs.items():
        if value is not None:
            normalized_key = _normalize_config_key(key)
            validated_value = _validate_config_value(key, value)
            cfg_mgr.set_config(normalized_key, validated_value)
    return display_config()


def reset_config() -> bool:
    """
    Reset persisted user configuration back to defaults.
    """
    cfg_mgr = ConfigManager()
    return cfg_mgr.reset_to_defaults()


def health_check() -> Tuple[bool, list[str]]:
    """
    Run VeriSift dependency checks and return status and missing items.
    """
    return run_health_check(exit_on_failure=False)


def create_comparator(config: Optional[VerisiftConfig] = None) -> Comparator:
    """
    Create a Comparator instance for programmatic use.
    If config is omitted, the persisted user config is used.
    """
    return Comparator(config or load_config())


def compare_pdfs(
    actual: str,
    expected: str,
    config: Optional[VerisiftConfig] = None,
) -> ComparisonReport:
    """
    High-level developer API for comparing two PDF files.

    Args:
        actual_path: Path to the actual PDF.
        expected_path: Path to the expected PDF.
        config: Optional VeriSift configuration. If omitted, defaults are used.

    Returns:
        ComparisonReport: Structured comparison result.
    """
    comparator = create_comparator(config)
    return comparator.compare(actual_path=actual, expected_path=expected)


def generate_report(
    report: ComparisonReport,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate an HTML report from an existing comparison result.

    Args:
        report: Previously generated comparison report object.
        output_path: Optional destination path for the HTML report.

    Returns:
        str: Final output path of the generated HTML report.
    """
    final_output_path: str
    if output_path is None:
        report_name = str(report.configuration.get("report_name", VerisiftConfig.report_name))
        output_dir = str(report.configuration.get("output_dir", VerisiftConfig.output_dir))
        final_output_path = os.path.join(output_dir, report_name)
    else:
        final_output_path = output_path

    output_dirname = os.path.dirname(final_output_path)
    if output_dirname:
        os.makedirs(output_dirname, exist_ok=True)

    if not generate_html_report(report, final_output_path):
        raise RuntimeError(f"Failed to generate HTML report at: {final_output_path}")

    return final_output_path


def compare_and_generate_report(
    actual: str,
    expected: str,
    config: Optional[VerisiftConfig] = None,
    output_path: Optional[str] = None,
) -> tuple[ComparisonReport, str]:
    """
    Compare two PDFs and generate an HTML report in one call.

    Args:
        actual_path: Path to the actual PDF.
        expected_path: Path to the expected PDF.
        config: Optional VeriSift configuration. If omitted, defaults are used.
        output_path: Optional destination path for the HTML report.

    Returns:
        tuple[ComparisonReport, str]: The comparison result and generated report path.
    """
    report: ComparisonReport = compare_pdfs(actual, expected, config=config)
    report_path: str = generate_report(report, output_path=output_path)
    return report, report_path
