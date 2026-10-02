#!/usr/bin/env python3
"""Extract source order, text, tables, metadata, and media from md/txt/docx."""

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CORE = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DCTERMS = "{http://purl.org/dc/terms/}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DRAWING = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WORD_DRAWING = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"


def text_of(element):
    return "".join(node.text or "" for node in element.iter() if node.tag == WORD + "t")


def paragraph(element, numbering=None, relationships=None, media_targets=None):
    properties = element.find(WORD + "pPr")
    style = None
    list_info = None
    if properties is not None:
        style_node = properties.find(WORD + "pStyle")
        if style_node is not None:
            style = style_node.get(WORD + "val")
        num_properties = properties.find(WORD + "numPr")
        if num_properties is not None:
            num_id_node = num_properties.find(WORD + "numId")
            level_node = num_properties.find(WORD + "ilvl")
            num_id = num_id_node.get(WORD + "val") if num_id_node is not None else None
            level = int(level_node.get(WORD + "val", "0")) if level_node is not None else 0
            number_format = (numbering or {}).get((num_id, level), "decimal")
            list_info = {"level": level, "ordered": number_format != "bullet", "format": number_format}
    runs = []
    for child in element:
        hyperlink = child.tag == WORD + "hyperlink"
        href = (relationships or {}).get(child.get(REL + "id")) if hyperlink else None
        candidates = child.findall(WORD + "r") if hyperlink else ([child] if child.tag == WORD + "r" else [])
        for run in candidates:
            value = text_of(run)
            if not value:
                continue
            item = {"text": value}
            properties = run.find(WORD + "rPr")
            if properties is not None and properties.find(WORD + "b") is not None:
                item["bold"] = True
            if href:
                item["href"] = href
            runs.append(item if len(item) > 1 else value)
    result = {"type": "paragraph", "style": style, "text": text_of(element)}
    if any(isinstance(run, dict) for run in runs):
        result["runs"] = runs
    images = []
    for drawing in element.iter(DRAWING + "blip"):
        relation_id = drawing.get(REL + "embed")
        source = (media_targets or {}).get(relation_id)
        if not source:
            continue
        description = ""
        for properties_node in element.iter(WORD_DRAWING + "docPr"):
            description = properties_node.get("descr") or properties_node.get("name") or ""
            if description:
                break
        images.append({"src": source, "alt": description or Path(source).stem})
    if images:
        result["images"] = images
    if list_info:
        result["list"] = list_info
    return result


def numbering_map(archive):
    if "word/numbering.xml" not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read("word/numbering.xml"))
    abstract_formats = {}
    for abstract in root.findall(WORD + "abstractNum"):
        abstract_id = abstract.get(WORD + "abstractNumId")
        levels = {}
        for level in abstract.findall(WORD + "lvl"):
            level_id = int(level.get(WORD + "ilvl", "0"))
            format_node = level.find(WORD + "numFmt")
            levels[level_id] = format_node.get(WORD + "val", "decimal") if format_node is not None else "decimal"
        abstract_formats[abstract_id] = levels
    result = {}
    for num in root.findall(WORD + "num"):
        num_id = num.get(WORD + "numId")
        abstract_node = num.find(WORD + "abstractNumId")
        abstract_id = abstract_node.get(WORD + "val") if abstract_node is not None else None
        for level, number_format in abstract_formats.get(abstract_id, {}).items():
            result[(num_id, level)] = number_format
    return result


def table(element):
    rows = []
    for row in element.findall(WORD + "tr"):
        cells = []
        for cell in row.findall(WORD + "tc"):
            cells.append("\n".join(text_of(p) for p in cell.findall(WORD + "p") if text_of(p)))
        rows.append(cells)
    return {"type": "table", "rows": rows}


def extract_docx(path, media_dir):
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        body = document.find(WORD + "body")
        numbering = numbering_map(archive)
        relationships = {}
        media_targets = {}
        relations_path = "word/_rels/document.xml.rels"
        if relations_path in archive.namelist():
            relations = ET.fromstring(archive.read(relations_path))
            for relation in relations.findall(PACKAGE_REL + "Relationship"):
                relation_id = relation.get("Id")
                target = relation.get("Target", "")
                if relation.get("TargetMode") == "External":
                    relationships[relation_id] = target
                elif target.startswith("media/"):
                    media_targets[relation_id] = str(media_dir / Path(target).name)
        blocks = []
        for child in body:
            if child.tag == WORD + "p":
                blocks.append(paragraph(child, numbering, relationships, media_targets))
            elif child.tag == WORD + "tbl":
                blocks.append(table(child))
        metadata = {}
        if "docProps/core.xml" in archive.namelist():
            core = ET.fromstring(archive.read("docProps/core.xml"))
            for name, tag in (("author", "{http://purl.org/dc/elements/1.1/}creator"),
                              ("created_at", DCTERMS + "created")):
                node = core.find(tag)
                if node is not None and node.text:
                    metadata[name] = node.text
        media = []
        used_names = set()
        for item in archive.namelist():
            if not item.startswith("word/media/") or item.endswith("/"):
                continue
            name = Path(item).name
            if name in used_names:
                continue
            used_names.add(name)
            media_dir.mkdir(parents=True, exist_ok=True)
            target = media_dir / name
            target.write_bytes(archive.read(item))
            media.append(str(target))
    return {"source": str(path), "metadata": metadata, "blocks": blocks, "media": media,
            "warning": "Standard OOXML image order, numbering, emphasis and hyperlinks were recovered; visually compare unusual Word fields or floating layouts."}


def extract_text(path):
    content = path.read_text(encoding="utf-8-sig")
    groups = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
    return {"source": str(path), "metadata": {},
            "blocks": [{"type": "source-text", "text": group.strip()} for group in groups if group.strip()],
            "media": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    suffix = args.source.suffix.lower()
    if suffix == ".docx":
        result = extract_docx(args.source, args.output_json.parent / "extracted-media")
    elif suffix in {".md", ".markdown", ".txt"}:
        result = extract_text(args.source)
    else:
        raise SystemExit(f"Unsupported source: {suffix}. Convert legacy .doc to .docx first.")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output_json.resolve())


if __name__ == "__main__":
    main()
