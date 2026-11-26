import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = ROOT / "artifacts"

class SiteHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if "id" in attr_dict:
            self.ids.add(attr_dict["id"])
        if tag == "img" and "src" in attr_dict:
            self.refs.append(("HTML <img>", attr_dict["src"]))
        elif tag == "link" and attr_dict.get("rel") == "stylesheet" and "href" in attr_dict:
            self.refs.append(("HTML <link>", attr_dict["href"]))
        elif tag == "a" and "href" in attr_dict:
            self.refs.append(("HTML <a>", attr_dict["href"]))

def is_local(ref: str) -> bool:
   return bool(ref) and not ref.startswith(("http://", "https://", "//", "data:", "mailto:"))

def main() -> int:
    missing = []
    checked = 0

    index_path = ROOT / "index.html"
    parser = SiteHTMLParser()
    parser.feed(index_path.read_text(encoding="utf-8"))

    for kind, ref in parser.refs:
        if not is_local(ref):
            continue
        checked += 1
        if ref.startswith("#"):
            if len(ref) > 1 and ref[1:] not in parser.ids:
                missing.append(f"[index.html] {kind} broken anchor: {ref}")
        else:
            target = (index_path.parent / ref).resolve()
            if not target.is_file():
                missing.append(f"[index.html] {kind} missing file: {ref}")

    for css_file in sorted((ROOT / "css").glob("*.css")):
        content = css_file.read_text(encoding="utf-8")
        for match in re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", content):
            if is_local(match):
                checked += 1
                target = (css_file.parent / match).resolve()
                if not target.is_file():
                    missing.append(f"[css/{css_file.name}] CSS url() missing file: {match}")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines = [
        f"Python Version: {sys.version.split()[0]}",
        f"Checked References: {checked}",
        f"Missing References: {len(missing)}",
    ]
    if missing:
        report_lines.append("Failures:")
        report_lines.extend(f"  - {m}" for m in missing)
    else:
        report_lines.append("Status: PASSED")

    report_text = "\n".join(report_lines) + "\n"
    (ARTIFACT_DIR / "asset-audit-report.txt").write_text(report_text, encoding="utf-8")
    print(report_text.strip())

    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())