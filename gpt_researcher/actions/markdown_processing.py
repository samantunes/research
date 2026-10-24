import re
import markdown
from typing import List, Dict

def extract_headers(markdown_text: str) -> List[Dict]:
    """
    Extract headers from markdown text.

    Args:
        markdown_text (str): The markdown text to process.

    Returns:
        List[Dict]: A list of dictionaries representing the header structure.
    """
    if not isinstance(markdown_text, str) or not markdown_text:
        return []
    headers = []
    parsed_md = markdown.markdown(markdown_text)
    lines = parsed_md.split("\n")

    stack = []
    for line in lines:
        if line.startswith("<h") and len(line) > 2 and line[2].isdigit():
            level = int(line[2])
            header_text = line[line.index(">") + 1 : line.rindex("<")]

            while stack and stack[-1]["level"] >= level:
                stack.pop()

            header = {
                "level": level,
                "text": header_text,
            }
            if stack:
                stack[-1].setdefault("children", []).append(header)
            else:
                headers.append(header)

            stack.append(header)

    return headers

def extract_sections(markdown_text: str) -> List[Dict[str, str]]:
    """
    Extract all written sections from subtopic report.

    Args:
        markdown_text (str): Subtopic report text.

    Returns:
        List[Dict[str, str]]: List of sections, each section is a dictionary containing
        'section_title' and 'written_content'.
    """
    if not isinstance(markdown_text, str) or not markdown_text:
        return []
    sections = []
    parsed_md = markdown.markdown(markdown_text)
    
    pattern = r'<h\d>(.*?)</h\d>(.*?)(?=<h\d>|$)'
    matches = re.findall(pattern, parsed_md, re.DOTALL)
    
    for title, content in matches:
        clean_content = re.sub(r'<.*?>', '', content).strip()
        if clean_content:
            sections.append({
                "section_title": title.strip(),
                "written_content": clean_content
            })
    
    return sections

def table_of_contents(markdown_text: str) -> str:
    """
    Generate a table of contents for the given markdown text.

    Args:
        markdown_text (str): The markdown text to process.

    Returns:
        str: The generated table of contents.
    """
    if not isinstance(markdown_text, str):
        return ""

    def generate_table_of_contents(headers, indent_level=0):
        toc = ""
        for header in headers:
            toc += " " * (indent_level * 4) + "- " + header["text"] + "\n"
            if "children" in header:
                toc += generate_table_of_contents(header["children"], indent_level + 1)
        return toc

    try:
        headers = extract_headers(markdown_text)
        toc = "## Table of Contents\n\n" + generate_table_of_contents(headers)
        return toc
    except Exception as e:
        print("table_of_contents Exception : ", e)
        return markdown_text

def add_references(report_markdown: str, visited_urls: set) -> str:
    """
    Add references to the markdown report.

    Args:
        report_markdown (str): The existing markdown report.
        visited_urls (set): A set of URLs that have been visited during research.

    Returns:
        str: The updated markdown report with added references.
    """
    if not isinstance(report_markdown, str):
        report_markdown = "" if report_markdown is None else str(report_markdown)
    if visited_urls is None:
        return report_markdown
    try:
        from .retriever import filter_low_authority_urls, rerank_sources_by_authority
        filtered = filter_low_authority_urls(list(visited_urls))
        ranked = rerank_sources_by_authority(sorted(filtered))
        url_markdown = "\n\n\n## References\n\n"
        url_markdown += "".join(f"- [{url}]({url})\n" for url in ranked)
        return report_markdown + url_markdown
    except Exception as e:
        print(f"Encountered exception in adding source urls : {e}")
        return report_markdown


def ensure_complete_references(
    report_markdown: str,
    visited_urls: set | list | None = None,
    research_sources: list | None = None,
    context: str | list | None = None,
) -> str:
    """Ensure that the report has a complete References section.

    If the LLM truncated before writing references, or the references section is missing
    or incomplete due to token limits, programmatically appends a formatted References section
    from visited high-authority citations and research sources.
    """
    if not isinstance(report_markdown, str):
        report_markdown = "" if report_markdown is None else str(report_markdown)

    if not report_markdown.strip():
        return report_markdown

    # Check if a references / bibliography section header is already present
    has_references_header = bool(
        re.search(r"(?i)(?:^|\n)#+\s*(?:References|Bibliography|Sources|Works Cited)", report_markdown)
    )

    # Collect candidate URLs from visited_urls, research_sources, and context
    from .retriever import filter_low_authority_urls, rerank_sources_by_authority

    candidate_urls: list[str] = []

    if visited_urls:
        candidate_urls.extend(list(visited_urls))

    if research_sources:
        for s in research_sources:
            if isinstance(s, dict):
                url = s.get("href") or s.get("url") or ""
                if url:
                    candidate_urls.append(url)
            elif isinstance(s, str):
                candidate_urls.append(s)

    if context:
        ctx_str = "\n".join(context) if isinstance(context, list) else str(context)
        extracted = re.findall(r"https?://[^\s\]\)>\"',;]+", ctx_str)
        candidate_urls.extend(extracted)

    # Filter out low-authority noise
    filtered_urls = filter_low_authority_urls(candidate_urls)
    # Deduplicate while preserving order
    unique_urls = list(dict.fromkeys(filtered_urls))
    # Rerank by authority so high-authority domains appear first
    ranked_urls = rerank_sources_by_authority(unique_urls)

    # If the report already has a References section with at least one URL, leave it intact
    if has_references_header:
        ref_match = re.search(
            r"(?i)(?:^|\n)#+\s*(?:References|Bibliography|Sources|Works Cited)(.*)",
            report_markdown,
            re.DOTALL,
        )
        if ref_match and ("http://" in ref_match.group(1) or "https://" in ref_match.group(1)):
            return report_markdown

    if not ranked_urls:
        return report_markdown

    # Guard: if report was cut off mid-sentence (does not end in punctuation or newline)
    trimmed_report = report_markdown.rstrip()
    if trimmed_report and trimmed_report[-1] not in (".", "!", "?", ":", "`", "*", "#", "\n"):
        trimmed_report += "..."

    # Programmatically append high-authority references
    ref_lines = ["\n\n## References\n"]
    for url in ranked_urls:
        domain = re.sub(r"^https?://(?:www\.)?", "", url).split("/")[0]
        ref_lines.append(f"- [{domain}]({url})")

    return trimmed_report + "\n" + "\n".join(ref_lines) + "\n"
