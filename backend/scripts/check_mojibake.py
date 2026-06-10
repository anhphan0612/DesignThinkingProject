from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".venv", "__pycache__", "media", "staticfiles", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}

# Common UTF-8-as-Windows-1252 mojibake fragments seen in Vietnamese text.
# Use chr(...) so this scanner does not contain the marker text it rejects.
MOJIBAKE_MARKERS = (
    chr(0x00C3),
    chr(0x00C2),
    chr(0x00C4),
    chr(0x00C6),
    chr(0x00E1) + chr(0x00BA),
    chr(0x00E1) + chr(0x00BB),
)


def should_scan(path):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return not any(part in SKIP_DIRS for part in path.parts)


def main():
    failures = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            failures.append((path, 0, f"not valid UTF-8: {exc}"))
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(marker in line for marker in MOJIBAKE_MARKERS):
                failures.append((path, line_no, line.strip()))

    if failures:
        print("Mojibake or non-UTF-8 text detected:")
        for path, line_no, detail in failures:
            location = f"{path.relative_to(ROOT)}:{line_no}" if line_no else str(path.relative_to(ROOT))
            print(f"- {location}: {detail.encode('unicode_escape').decode()}")
        raise SystemExit(1)

    print("No mojibake markers detected.")


if __name__ == "__main__":
    main()
