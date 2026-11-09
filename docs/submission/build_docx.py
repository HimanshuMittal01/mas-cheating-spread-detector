"""Build submission.docx from report.md by filling the Apart template's XML (keeps its fonts, header block and footnote).

    python3 docs/submission/build_docx.py            # -> docs/submission/submission.docx

report.md shape: '# Title', 'Authors: Name (Affil); Name (Affil)', '## Abstract', then body sections.
Markdown subset: ## / ### / #### headings, paragraphs, '- ' bullets (2-space nesting), '1. ' lists,
pipe tables, ![caption](path) images, **bold**, *italic*, `code`, [text](url). Lines starting with '>' are dropped.
"""
import re
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
FONT = '<w:rFonts w:ascii="Old Standard TT" w:cs="Old Standard TT" w:eastAsia="Old Standard TT" w:hAnsi="Old Standard TT"/>'
MONO = '<w:rFonts w:ascii="Courier New" w:cs="Courier New" w:eastAsia="Courier New" w:hAnsi="Courier New"/>'
TEXT_W = 9360  # 6.5in in dxa
rels: list[str] = []  # extra relationships added while building
media: dict[str, Path] = {}
nums: list[int] = []  # restarted decimal lists


def rid(kind: str, target: str, external: bool = False) -> str:
    i = f"rIdX{len(rels) + 1}"
    t = {"link": "hyperlink", "img": "image"}[kind]
    rels.append(f'<Relationship Id="{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{t}" '
                f'Target="{escape(target)}"{" TargetMode=\"External\"" if external else ""}/>')
    return i


def runs(text: str, size: int | None = None, base: str = "") -> str:
    """Inline markdown -> w:r elements."""
    out = []
    sz = f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else ""
    for tok in re.split(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?<![\w*])\*[^*\s][^*]*?\*(?!\w))", text):
        if not tok:
            continue
        fmt, font = base, FONT
        if tok.startswith("**"):
            tok, fmt = tok[2:-2], fmt + '<w:b w:val="1"/><w:bCs w:val="1"/>'
        elif tok.startswith("`"):
            tok, font = tok[1:-1], MONO
        elif tok.startswith("[") and "](" in tok:
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok).groups()
            r = f'<w:r><w:rPr>{FONT}<w:color w:val="1155cc"/><w:u w:val="single"/>{sz}</w:rPr><w:t xml:space="preserve">{escape(label)}</w:t></w:r>'
            out.append(f'<w:hyperlink r:id="{rid("link", url, True)}">{r}</w:hyperlink>')
            continue
        elif tok.startswith("*") and len(tok) > 2:
            tok, fmt = tok[1:-1], fmt + '<w:i w:val="1"/><w:iCs w:val="1"/>'
        out.append(f'<w:r><w:rPr>{font}{fmt}{sz}</w:rPr><w:t xml:space="preserve">{escape(tok)}</w:t></w:r>')
    return "".join(out)


def para(text: str, ppr: str = "", size: int | None = None, base: str = "") -> str:
    return f'<w:p><w:pPr>{ppr or "<w:spacing w:after=\"100\"/>"}<w:jc w:val="both"/><w:rPr>{FONT}</w:rPr></w:pPr>{runs(text, size, base)}</w:p>'


def heading(level: int, text: str) -> str:
    style, sz, color, before = {2: ("Heading2", 28, "434343", 240), 3: ("Heading3", 24, "666666", 160), 4: ("", 22, "000000", 100)}[level]
    ps = f'<w:pStyle w:val="{style}"/>' if style else '<w:keepNext w:val="1"/>'
    rp = f'{FONT}<w:b w:val="1"/><w:bCs w:val="1"/><w:color w:val="{color}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    return (f'<w:p><w:pPr>{ps}<w:spacing w:before="{before}" w:after="60" w:line="276" w:lineRule="auto"/><w:rPr>{rp}</w:rPr></w:pPr>'
            f'<w:r><w:rPr>{rp}</w:rPr><w:t xml:space="preserve">{escape(re.sub(r"[*]", "", text))}</w:t></w:r></w:p>')


def list_item(text: str, num_id: int, lvl: int) -> str:
    ind = 720 + 360 * lvl
    ppr = (f'<w:numPr><w:ilvl w:val="{lvl}"/><w:numId w:val="{num_id}"/></w:numPr>'
           f'<w:spacing w:after="40"/><w:ind w:left="{ind}" w:hanging="360"/>')
    return para(text, ppr)


def table(rows: list[list[str]]) -> str:
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    weight = [max(6, min(40, max(len(re.sub(r"[*`]", "", r[c])) for r in rows))) for c in range(ncol)]
    widths = [int(TEXT_W * w / sum(weight)) for w in weight]
    widths[-1] += TEXT_W - sum(widths)
    b = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblBorders>'
           + "".join(b.format(s) for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
           + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"]
    for i, r in enumerate(rows):
        out.append("<w:tr>" + ('<w:trPr><w:tblHeader/></w:trPr>' if i == 0 else ""))
        for c, cell in enumerate(r):
            shd = '<w:shd w:val="clear" w:color="auto" w:fill="EFEFEF"/>' if i == 0 else ""
            bold = '<w:b w:val="1"/><w:bCs w:val="1"/>' if i == 0 else ""
            out.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[c]}" w:type="dxa"/>{shd}</w:tcPr>'
                       f'<w:p><w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/><w:rPr>{FONT}</w:rPr></w:pPr>'
                       f'{runs(cell.strip(), 17, bold)}</w:p></w:tc>')
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out) + '<w:p><w:pPr><w:spacing w:after="60"/></w:pPr></w:p>'


def png_size(p: Path) -> tuple[int, int]:
    return struct.unpack(">II", p.read_bytes()[16:24])


def image(caption: str, path: str) -> str:
    p = (HERE / path).resolve()
    name = f"img{len(media) + 1}.png"
    media[name] = p
    r = rid("img", f"media/{name}")
    w, h = png_size(p)
    cx = 5943600  # 6.5in in EMU
    cy = int(cx * h / w)
    n = len(media)
    pic = (f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{100 + n}" name="Figure {n}"/>'
           f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="{100 + n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{r}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
           f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>')
    return (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/></w:pPr><w:r>{pic}</w:r></w:p>'
            + para(caption, '<w:spacing w:after="160"/>', 19))


def blocks(md: str) -> str:
    out, buf, tbl = [], [], []
    num_id = None
    lines = md.splitlines() + [""]

    def flush():
        nonlocal buf
        if buf:
            out.append(para(" ".join(buf)))
            buf = []

    for ln in lines:
        s = ln.strip()
        if tbl and not s.startswith("|"):
            out.append(table(tbl))
            tbl = []
        if s.startswith("|"):
            flush()
            cells = [c for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in cells):
                tbl.append(cells)
            continue
        if not s or s == "---" or s.startswith(">"):
            flush()
            if not s:
                continue
            continue
        if m := re.match(r"(#{2,4}) (.*)", s):
            flush()
            num_id = None
            out.append(heading(len(m.group(1)), m.group(2)))
        elif m := re.match(r"!\[(.*)\]\((.*)\)", s):
            flush()
            out.append(image(m.group(1), m.group(2)))
        elif m := re.match(r"( *)- (.*)", ln):
            flush()
            out.append(list_item(m.group(2), 3, len(m.group(1)) // 2))
        elif m := re.match(r"( *)(\d+)\. (.*)", ln):
            flush()
            if m.group(2) == "1" and not m.group(1):
                nums.append(len(nums) + 100)
                num_id = nums[-1]
            out.append(list_item(m.group(3), num_id or 5, len(m.group(1)) // 3))
        else:
            buf.append(s)
    flush()
    return "".join(out)


def main(src=HERE / "report.md", tpl=HERE / "template.docx", dst=HERE / "submission.docx"):
    md = Path(src).read_text()
    title = re.search(r"^# (.+)$", md, re.M).group(1).replace("**", "")
    authors = [re.match(r"(.+?)\s*\((.+)\)", a.strip()).groups() for a in re.search(r"^Authors: (.+)$", md, re.M).group(1).split(";")]
    abstract = re.search(r"^## Abstract\n(.*?)(?=^## )", md, re.M | re.S).group(1).strip()
    body = md[re.search(r"^## Abstract\n.*?(?=^## )", md, re.M | re.S).end():]

    work = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(tpl) as z:
        z.extractall(work)
    doc = (work / "word/document.xml").read_text()

    doc = doc.replace(">PROJECT TITLE<", f">{escape(title)}<", 1)
    # author table is 3 x 690 dxa in the template (Google Docs autofits it; Word/LibreOffice do not): widen it
    a0 = doc.rindex("<w:tbl>", 0, doc.index(">Author name 1<"))
    a1 = doc.index("</w:tbl>", a0)
    seg = doc[a0:a1].replace('w:w="2070.0"', 'w:w="7800.0"').replace('w:w="690"', 'w:w="2600"').replace('w:w="690.0"', 'w:w="2600.0"')
    doc = doc[:a0] + seg + doc[a1:]
    for k in range(1, 7):
        name, aff = authors[k - 1] if k <= len(authors) else ("", "")
        i = doc.index(f">Author name {k}<")
        doc = doc[:i] + f">{escape(name)}<" + doc[i + len(f">Author name {k}<"):]
        j = doc.index(">Affiliation<", i)
        doc = doc[:j] + f">{escape(aff)}<" + doc[j + len(">Affiliation<"):]

    # abstract box: replace the guidance paragraph(s) inside its cell
    i = doc.index("Summarize your project")
    p0 = doc.rindex("<w:p ", 0, i)
    p1 = doc.index("</w:tc>", i)
    ab_ppr = f'<w:spacing w:after="120" w:line="240" w:lineRule="auto"/><w:ind w:left="540" w:right="45" w:firstLine="0"/>'
    doc = doc[:p0] + "".join(para(t.replace("\n", " "), ab_ppr) for t in abstract.split("\n\n")) + doc[p1:]

    # delete the info box table and everything from it to the end of the body; append ours
    i = doc.index("How to use this template")
    t0 = doc.rindex("<w:tbl>", 0, i)
    s0 = doc.index("<w:sectPr>")
    doc = doc[:t0] + blocks(body) + doc[s0:]
    doc = doc.replace('w:footer="720"/>', 'w:footer="720" w:gutter="0"/>')  # schema requires gutter
    (work / "word/document.xml").write_text(doc)

    rp = work / "word/_rels/document.xml.rels"
    rp.write_text(rp.read_text().replace("</Relationships>", "".join(rels) + "</Relationships>"))
    if media:
        (work / "word/media").mkdir(exist_ok=True)
        for n, p in media.items():
            shutil.copy(p, work / "word/media" / n)
        ct = work / "[Content_Types].xml"
        ct.write_text(ct.read_text().replace("<Default ", '<Default ContentType="image/png" Extension="png"/><Default ', 1))
    nf = work / "word/numbering.xml"
    nf.write_text(nf.read_text().replace("</w:numbering>", "".join(
        f'<w:num w:numId="{n}"><w:abstractNumId w:val="5"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
        for n in nums) + "</w:numbering>"))

    Path(dst).unlink(missing_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(work.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(work).as_posix())
    shutil.rmtree(work)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:])
