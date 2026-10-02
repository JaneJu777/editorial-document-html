import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from infer_article import infer_article  # noqa: E402
from validate_article import ArticleValidationError, validate_article  # noqa: E402


class InferenceTests(unittest.TestCase):
    def test_markdown_maps_structure_and_components(self):
        source = """# 自动映射示例

## 工作流程

1. 读取源文档
2. 识别内容结构
3. 生成页面

## 环境准备

前置条件：无
执行方式：自动检查源文件
验收标准：输出可以直接预览

## 设计原则

清晰：让层级一眼可辨
克制：避免不必要的视觉噪音
可追溯：保留来源与判断边界

## 数据比较

| 场景 | 优先级 |
| --- | --- |
| 产品愿景 | P0 |

## 交付方式对比

传统方式：经过多层转述
AI 原生方式：直接保留意图

> 风格不改变原始内容。

```python
print("ok")
```
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.md"
            path.write_text(source, encoding="utf-8")
            article = infer_article(path, style="notebook")
        self.assertEqual(article["title"], "自动映射示例")
        types = [block["type"] for chapter in article["chapters"] for block in chapter.get("blocks", [])]
        self.assertIn("flow", types)
        self.assertIn("keyvalue", types)
        self.assertIn("cards", types)
        self.assertIn("table", types)
        self.assertIn("compare", types)
        self.assertIn("quote", types)
        self.assertIn("code", types)
        code = next(block for chapter in article["chapters"] for block in chapter.get("blocks", []) if block["type"] == "code")
        self.assertEqual(code["language"], "python")
        table = next(block for chapter in article["chapters"] for block in chapter.get("blocks", []) if block["type"] == "table")
        self.assertEqual(table["rows"][0][1], {"text": "P0", "chip": "p0"})

    def test_unmarked_text_uses_conservative_logic(self):
        source = """产品设计说明

工作流程

1. 收集输入
2. 检查结构
3. 输出页面

结论：未明确标注的普通叙述仍然保留为正文。
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plain.txt"
            path.write_text(source, encoding="utf-8")
            article = infer_article(path)
        self.assertEqual(article["title"], "产品设计说明")
        blocks = [block for chapter in article["chapters"] for block in chapter.get("blocks", [])]
        self.assertTrue(any(block["type"] == "flow" for block in blocks))
        self.assertTrue(any(block["type"] == "callout" for block in blocks))
        self.assertTrue(article["mapping_report"])

    def test_nested_markdown_list_is_preserved_not_promoted(self):
        source = """# 示例\n\n## 工作流程\n\n1. 父步骤\n   - 子项目 A\n   - 子项目 B\n2. 第二步\n"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested.md"
            path.write_text(source, encoding="utf-8")
            article = infer_article(path)
        block = article["chapters"][0]["blocks"][0]
        self.assertEqual(block["type"], "list")
        self.assertEqual(block["items"][0]["children"], ["子项目 A", "子项目 B"])

    def test_docx_heading_and_numbering_are_recovered(self):
        document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>工作流程</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>读取文档</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>生成页面</w:t></w:r></w:p>
</w:body></w:document>"""
        numbering_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
                archive.writestr("word/numbering.xml", numbering_xml)
            article = infer_article(path, title_override="DOCX 示例")
        self.assertEqual(article["chapters"][0]["title"], "工作流程")
        self.assertEqual(article["chapters"][0]["blocks"][0]["type"], "flow")

    def test_docx_inline_semantics_and_image_position_are_recovered(self):
        document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body>
<w:p><w:r><w:t>这是</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>重点内容</w:t></w:r>
<w:hyperlink r:id="rIdLink"><w:r><w:t>来源</w:t></w:r></w:hyperlink><w:r><w:t>。</w:t></w:r></w:p>
<w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" name="图示" descr="流程图"/>
<a:graphic><a:graphicData><a:blip r:embed="rIdImage"/></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
</w:body></w:document>"""
        relations_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdLink" Target="https://example.com" TargetMode="External" Type="x"/>
<Relationship Id="rIdImage" Target="media/image1.png" Type="x"/>
</Relationships>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inline.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
                archive.writestr("word/_rels/document.xml.rels", relations_xml)
                archive.writestr("word/media/image1.png", b"png")
            article = infer_article(path, title_override="DOCX")
        blocks = article["chapters"][0]["blocks"]
        self.assertEqual(blocks[0]["content"][1], {"text": "重点内容", "bold": True})
        self.assertEqual(blocks[0]["content"][2]["href"], "https://example.com")
        self.assertEqual(blocks[1]["type"], "image")
        self.assertEqual(blocks[1]["alt"], "流程图")


class ValidationAndRenderTests(unittest.TestCase):
    def test_sample_validates_and_all_styles_render(self):
        titles = set()
        with tempfile.TemporaryDirectory() as directory:
            for style in ("editorial", "newsroom", "humanist-blog", "notebook"):
                sample = ROOT / "examples" / f"{style}-preview.json"
                data = json.loads(sample.read_text(encoding="utf-8"))
                validate_article(data)
                self.assertEqual(data["style"], style)
                titles.add(data["title"])
                output = Path(directory) / f"{style}.html"
                subprocess.run([sys.executable, str(ROOT / "scripts" / "render_article.py"),
                                str(sample), str(output), "--style", style], check=True,
                               capture_output=True, text=True)
                html = output.read_text(encoding="utf-8")
                self.assertIn(f'data-style="{style}"', html)
                self.assertIn('id="edit"', html)
                self.assertIn('id="edit-save"', html)
                self.assertIn('id="edit-cancel"', html)
                self.assertIn("editorial-content-edits:v1:", html)
                self.assertIn("contenteditable', 'true", html)
                if style == "humanist-blog":
                    self.assertIn('class="language-json"', html)
                    self.assertNotIn('class="card-icon"', html)
                if style == "editorial":
                    self.assertIn('<span class="card-icon" aria-hidden="true">🎯</span> 用户价值', html)
                    self.assertIn('<span class="card-icon" aria-hidden="true">📈</span> 业务杠杆', html)
                    self.assertIn('<span class="card-icon" aria-hidden="true">✅</span> 交付把握', html)
                self.assertNotIn("__FONT_DIR__", html)
                self.assertTrue((output.parent / f"{style}-assets" / "fonts").is_dir())
        self.assertEqual(len(titles), 4)

    def test_legacy_style_alias_renders_as_humanist_blog(self):
        sample = ROOT / "examples" / "humanist-blog-preview.json"
        data = json.loads(sample.read_text(encoding="utf-8"))
        data["style"] = "claude-blog"
        validate_article(data)
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy.json"
            output = Path(directory) / "legacy.html"
            legacy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "render_article.py"),
                            str(legacy), str(output)], check=True, capture_output=True, text=True)
            html = output.read_text(encoding="utf-8")
        self.assertIn('data-style="humanist-blog"', html)
        self.assertNotIn('data-style="claude-blog"', html)

    def test_validator_rejects_missing_image_alt(self):
        article = {"title": "x", "chapters": [{"title": "x", "blocks": [
            {"type": "image", "src": "x.png", "alt": ""}
        ]}]}
        with self.assertRaises(ArticleValidationError):
            validate_article(article)


if __name__ == "__main__":
    unittest.main()
