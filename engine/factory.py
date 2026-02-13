from engine.format_1 import parse as parse_format_1
from engine.format_2 import parse as parse_format_2

PARSER_MAP = {
    "format_1": parse_format_1,
    "format_2": parse_format_2,
}

def run_parser(text: str, format_type: str):
    parser = PARSER_MAP.get(format_type)
    if not parser:
        raise ValueError(f"Format '{format_type}' tidak dikenali")
    return parser(text)
