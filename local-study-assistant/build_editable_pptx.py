"""Build an editable PowerPoint from native DrawingML shapes and embedded UI captures."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

ROOT = Path(__file__).parent
OUT = ROOT / "local-study-assistant-presentation.pptx"
EMU = 914400
SW, SH = 13.333333, 7.5
BG, PANEL, LINE = "0B0712", "181022", "50366D"
INK, MUTED, PURPLE, PINK, GREEN = "F4EDFF", "C1B5D4", "C69AFF", "ED8BFF", "9EE8C1"

def e(inches):
    return str(round(inches * EMU))

def solid(color, alpha=None):
    a = f'<a:alpha val="{alpha}"/>' if alpha else ""
    return f'<a:solidFill><a:srgbClr val="{color}">{a}</a:srgbClr></a:solidFill>'

def shape_xml(sid, name, x, y, w, h, fill=None, line=None, geom="rect", text=None,
              size=1800, color=INK, bold=False, font="Aptos", align="l", valign="ctr",
              margin=0.12, italic=False):
    if text is None:
        tx = ""
    else:
        paras = []
        for para in str(text).split("\n"):
            paras.append(f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="en-US" sz="{size}" b="{1 if bold else 0}" i="{1 if italic else 0}">{solid(color)}<a:latin typeface="{font}"/></a:rPr><a:t xml:space="preserve">{escape(para)}</a:t></a:r><a:endParaRPr lang="en-US" sz="{size}"/></a:p>')
        tx = f'<p:txBody><a:bodyPr wrap="square" anchor="{valign}" lIns="{e(margin)}" rIns="{e(margin)}" tIns="{e(margin)}" bIns="{e(margin)}"/><a:lstStyle/>{"".join(paras)}</p:txBody>'
    fill_xml = solid(fill) if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="12700">{solid(line)}<a:prstDash val="solid"/></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>{tx}</p:sp>')

def pic_xml(sid, name, rel, x, y, w, h):
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rel}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr><a:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:ln><a:noFill/></a:ln></p:spPr></p:pic>')

def group_start():
    return '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'

slides = []
def new_slide(label, kicker, title, page):
    body = [shape_xml(2, "Background", 0, 0, SW, SH, BG),
            shape_xml(3, "Accent glow", 9.1, -0.25, 4.25, 2.1, "291A41", geom="ellipse"),
            shape_xml(4, "Brand", 0.62, 0.38, 8.7, 0.38, text=f"●   LOCAL STUDY ASSISTANT     /     {label.upper()}", size=900, color=PURPLE, bold=True),
            shape_xml(5, "Page number", 11.92, 0.38, 0.75, 0.3, text=page, size=900, color="8F7FA7", align="r"),
            shape_xml(6, "Kicker", 0.7, 0.98, 11.8, 0.28, text=kicker.upper(), size=900, color=PINK, bold=True),
            shape_xml(7, "Slide title", 0.67, 1.28, 12.0, 0.65, text=title, size=2900, color=INK, bold=True)]
    slides.append((body, []))
    return body

def add_card(body, x, y, w, h, eyebrow, title, desc, n, title_size=1600, desc_size=1150):
    body.append(shape_xml(n, f"{title} card", x, y, w, h, PANEL, LINE, geom="roundRect"))
    body.append(shape_xml(n+1, f"{title} label", x+0.17, y+0.16, w-0.34, 0.25, text=eyebrow.upper(), size=800, color=PINK, bold=True))
    body.append(shape_xml(n+2, f"{title} heading", x+0.17, y+0.48, w-0.34, 0.5, text=title, size=title_size, color=PURPLE, bold=True))
    body.append(shape_xml(n+3, f"{title} description", x+0.17, y+1.03, w-0.34, h-1.15, text=desc, size=desc_size, color=MUTED, valign="t"))

def add_footer(body, text="LOCAL STUDY ASSISTANT   •   LOCAL-FIRST STUDY WORKFLOW"):
    body.append(shape_xml(250, "Footer rule", 0.68, 7.12, 12.0, 0.015, PURPLE))
    body.append(shape_xml(251, "Footer", 0.72, 7.15, 11.7, 0.18, text=text, size=650, color="8F7FA7"))

# 1 — Cover
b = new_slide("Product guide", "ITRI626  ·  Local AI", "Course notes in.\nClearer study out.", "01 / 07")
b[4] = shape_xml(6, "Kicker", 0.7, 1.05, 11.8, 0.3, text="A SOURCE-GROUNDED STUDY COMPANION", size=950, color=PINK, bold=True)
b[5] = shape_xml(7, "Slide title", 0.68, 1.55, 11.8, 1.4, text="Course notes in.\nClearer study out.", size=3800, color=INK, bold=True)
b.append(shape_xml(8, "Cover description", 0.72, 3.25, 10.8, 0.72, text="A local assistant searches your learning materials, asks a locally hosted language model for help, and points back to the sources it used.", size=1750, color=MUTED, valign="t"))
flow = [("YOUR NOTES",0.72),("LOCAL SEARCH",3.65),("LOCAL MODEL",6.58),("STUDY RESPONSE",9.51)]
for i,(txt,x) in enumerate(flow):
    b.append(shape_xml(20+i, f"Workflow {txt}", x, 5.05, 2.35, 0.72, PANEL, LINE, "roundRect", f"●   {txt}", 1050, INK, True, align="ctr"))
    if i < 3: b.append(shape_xml(30+i,"Workflow arrow",x+2.42,5.22,0.35,0.35,text="→",size=1800,color=PINK,bold=True,align="ctr"))
add_footer(b, "A WALKTHROUGH OF THE APP, ITS ARCHITECTURE, AND HOW TO USE IT")

# 2 — App UI walkthrough
b = new_slide("Product tour", "One workspace · Three jobs", "Three panels. One study loop.", "02 / 07")
b.append(shape_xml(10,"Screenshot frame",0.72,2.15,6.7,4.45,"100C15",LINE,"roundRect"))
b.append(pic_xml(11,"App workspace screenshot","rId2",1.75,2.25,4.55,4.23))
for i,(head,desc) in enumerate([
    ("Sources","Add PDF, TXT, or Markdown materials, then index them for search."),
    ("Notebook chat","Choose a mode, write a prompt, and set how many excerpts to retrieve."),
    ("Studio","Switch between question answering, quiz generation, and feedback.")]):
    y=2.28+i*1.34
    b.append(shape_xml(20+i*3,f"Number {i+1}",7.85,y,0.42,0.42,PANEL,PURPLE,"ellipse",str(i+1),1050,PURPLE,True,align="ctr"))
    b.append(shape_xml(21+i*3,f"{head} heading",8.45,y,4.0,0.35,text=head,size=1650,color=INK,bold=True))
    b.append(shape_xml(22+i*3,f"{head} description",8.45,y+0.4,4.1,0.72,text=desc,size=1150,color=MUTED,valign="t"))
b.append(shape_xml(40,"Screenshot disclosure",7.85,6.33,4.6,0.38,text="Screenshot uses an illustrative source filename.",size=850,color="A895BD",italic=True))
add_footer(b)

# 3 — RAG pipeline
b = new_slide("How it works", "Retrieval-augmented generation", "Search first. Ask the model second.", "03 / 07")
b.append(shape_xml(10,"Explanation",0.72,2.0,11.7,0.58,text="Uploaded files do not train the model. The app retrieves relevant text and passes it as temporary context with each request.",size=1400,color=MUTED))
steps=[("01 · INGEST","PDF / TXT / MD","Read text; PDF pages retain page numbers."),("02 · CHUNK","~1,000 chars","Normalize text into chunks with 150-character overlap."),("03 · INDEX","SQLite FTS5","Porter stemming and Unicode tokenization."),("04 · RETRIEVE","Top excerpts","Keyword match, rank, and select the requested limit."),("05 · PROMPT","Notes + instructions","Ask for a response grounded in the retrieved excerpts."),("06 · RESPOND","Local model","Return the answer and source list to the interface.")]
for i,(ey,title,desc) in enumerate(steps):
    x=0.72+i*2.08
    b.append(shape_xml(20+i*4,f"Pipeline {i+1}",x,3.0,1.88,2.3,PANEL,LINE,"roundRect"))
    b.append(shape_xml(21+i*4,"Pipeline label",x+0.12,3.18,1.65,0.32,text=ey,size=730,color=PINK,bold=True))
    b.append(shape_xml(22+i*4,"Pipeline heading",x+0.12,3.62,1.65,0.45,text=title,size=1250,color=PURPLE,bold=True))
    b.append(shape_xml(23+i*4,"Pipeline detail",x+0.12,4.15,1.65,0.92,text=desc,size=920,color=MUTED,valign="t"))
    if i<5: b.append(shape_xml(60+i,"Pipeline arrow",x+1.87,3.9,0.2,0.3,text="›",size=1700,color=PINK,bold=True,align="ctr"))
for j,(x,w,ey,head,desc) in enumerate([(0.72,5.75,"SEARCH DETAILS","Keyword retrieval","Up to 12 query terms are OR-matched; ranked results default to five excerpts."),(6.68,5.9,"GROUNDING DETAILS","Citations","The model sees labeled excerpts and is instructed to cite them or say when notes do not support an answer.")]):
    b.append(shape_xml(80+j*4,f"{head} card",x,5.62,w,1.18,PANEL,LINE,"roundRect"))
    b.append(shape_xml(81+j*4,"Details label",x+0.16,5.74,w-0.32,0.2,text=ey,size=700,color=PINK,bold=True))
    b.append(shape_xml(82+j*4,"Details heading",x+0.16,5.94,w-0.32,0.27,text=head,size=1050,color=PURPLE,bold=True))
    b.append(shape_xml(83+j*4,"Details description",x+0.16,6.23,w-0.32,0.45,text=desc,size=770,color=MUTED,valign="t"))
add_footer(b)

# 4 — How to use
b = new_slide("Getting started", "A simple study loop", "From a file to a focused question.", "04 / 07")
for i,(head,desc) in enumerate([
    ("Start the local model","Run Unsloth Studio, load a compatible GGUF instruct model, and make sure its local API is available."),
    ("Add course material","Choose PDF, TXT, or Markdown files in the Sources pane; uploads are stored locally."),
    ("Index your files","Select Index. Text is extracted, chunked, and written to the SQLite search index."),
    ("Ask and inspect","Choose a mode, enter a question, then review the cited source list under the response.")]):
    x=0.72+i*3.13
    b.append(shape_xml(20+i*4,f"Step {i+1} card",x,2.45,2.82,3.35,PANEL,LINE,"roundRect"))
    b.append(shape_xml(21+i*4,"Step number",x+0.18,2.7,2.35,0.3,text=f"STEP 0{i+1}",size=900,color=PINK,bold=True))
    b.append(shape_xml(22+i*4,"Step title",x+0.18,3.2,2.43,0.78,text=head,size=1700,color=PURPLE,bold=True,valign="t"))
    b.append(shape_xml(23+i*4,"Step details",x+0.18,4.1,2.43,1.35,text=desc,size=1150,color=MUTED,valign="t"))
b.append(shape_xml(50,"PDF note",0.75,6.12,11.9,0.45,text="PDF note: text must be selectable. Scanned pages need OCR, which is not included.",size=1100,color=PINK))
add_footer(b)

# 5 — modes and screenshot
b = new_slide("Study modes", "Three ways to use the same sources", "Ask. Practise. Explain what you know.", "05 / 07")
b.append(shape_xml(10,"Answer screenshot frame",0.72,2.2,5.55,4.45,"100C15",LINE,"roundRect"))
b.append(pic_xml(11,"Illustrative answer and citation","rId2",0.84,2.82,5.31,2.90))
for i,(head,desc) in enumerate([
    ("ASK","Get a course-focused explanation grounded in retrieved excerpts."),
    ("QUIZ","Generate three short practice questions; answers are withheld initially."),
    ("FEEDBACK","Review what is correct, what to improve, and a suggested model answer.")]):
    y=2.24+i*1.25
    b.append(shape_xml(20+i*2,f"{head} label",6.78,y,1.25,0.3,text=head,size=900,color=PINK,bold=True))
    b.append(shape_xml(21+i*2,f"{head} detail",6.78,y+0.35,5.35,0.68,text=desc,size=1300,color=INK))
b.append(shape_xml(30,"Citation explanation",6.78,6.12,5.45,0.44,text="Expand Sources used to inspect the file and PDF page. The pictured answer and citation are illustrative.",size=900,color="A895BD",italic=True))
add_footer(b)

# 6 — Technology
b = new_slide("Technology", "Small, local-first stack", "Every layer has a clear job.", "06 / 07")
stack=[("INTERFACE","HTML · CSS · JavaScript","Single-page browser UI; no frontend framework required."),("WEB SERVER","Python 3.11–3.13","Standard-library HTTP server serves the UI and local API."),("DOCUMENT PARSING","pypdf","Extracts selectable PDF text and page references."),("SEARCH INDEX","SQLite FTS5","Embedded full-text search with Porter stemming and Unicode tokenization."),("INFERENCE","Unsloth Studio","Serves a loaded local GGUF instruct model."),("MODEL API","OpenAI-compatible","/v1/chat/completions; temperature 0.3, up to 500 tokens by default.")]
for i,(ey,head,desc) in enumerate(stack):
    col=i%3; row=i//3; x=0.72+col*4.17; y=2.25+row*2.05
    b.append(shape_xml(20+i*4,f"{head} card",x,y,3.82,1.74,PANEL,LINE,"roundRect"))
    b.append(shape_xml(21+i*4,"Technology layer",x+0.17,y+0.16,3.46,0.24,text=ey,size=800,color=PINK,bold=True))
    b.append(shape_xml(22+i*4,"Technology name",x+0.17,y+0.52,3.46,0.42,text=head,size=1500,color=PURPLE,bold=True))
    b.append(shape_xml(23+i*4,"Technology description",x+0.17,y+1.02,3.46,0.55,text=desc,size=1000,color=MUTED,valign="t"))
add_footer(b)

# 7 — Privacy and limits
b = new_slide("Design boundaries", "Local by design · Evidence matters", "Know what stays local—and what to verify.", "07 / 07")
add_card(b,0.72,2.3,5.78,3.76,"Local","Your study loop","• The server binds to 127.0.0.1 on this computer.\n• Uploaded files, extracted text, and the SQLite index stay in local folders.\n• Model requests go to the configured local Unsloth endpoint.\n• API key can come from the Linux keyring or UNSLOTH_API_KEY.",20,1900,1150)
add_card(b,6.72,2.3,5.88,3.76,"Current limitations","What to keep in mind","• Retrieval uses keywords, not semantic search.\n• Scanned PDFs need OCR.\n• Small models can be incomplete or wrong; verify citations.\n• Chat history is not retained after refresh.\n• Uploaded sources do not fine-tune model weights.",40,1900,1150)
b.append(shape_xml(60,"Best practice",0.75,6.28,11.7,0.4,text="Best practice: start with a few clean files, verify indexed text, and evaluate with a fixed question set.",size=1150,color=PINK,bold=True))
add_footer(b)

def slide_xml(items):
    tree = group_start()+"".join(items)+"</p:spTree>"
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgPr>{solid(BG)}<a:effectLst/></p:bgPr></p:bg>{tree}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''

def theme_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Local Study Purple"><a:themeElements><a:clrScheme name="Purple"><a:dk1><a:srgbClr val="{BG}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="{PANEL}"/></a:dk2><a:lt2><a:srgbClr val="F4EDFF"/></a:lt2><a:accent1><a:srgbClr val="{PURPLE}"/></a:accent1><a:accent2><a:srgbClr val="{PINK}"/></a:accent2><a:accent3><a:srgbClr val="{GREEN}"/></a:accent3><a:accent4><a:srgbClr val="8C68D9"/></a:accent4><a:accent5><a:srgbClr val="50366D"/></a:accent5><a:accent6><a:srgbClr val="B4A7CB"/></a:accent6><a:hlink><a:srgbClr val="C69AFF"/></a:hlink><a:folHlink><a:srgbClr val="ED8BFF"/></a:folHlink></a:clrScheme><a:fontScheme name="Aptos"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme><a:fmtScheme name="Simple"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'''

def master_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld>{group_start()}</p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'''

def layout_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank">{group_start()}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'''

content_types=['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>','<Default Extension="xml" ContentType="application/xml"/>','<Default Extension="png" ContentType="image/png"/>','<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>','<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>','<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>','<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>']
content_types += [f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1,8)]
rels_root='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>'''
presentation=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId8"/></p:sldMasterIdLst><p:sldIdLst>{''.join(f'<p:sldId id="{256+i}" r:id="rId{i}"/>' for i in range(1,8))}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="wide"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>'''
pres_rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'''+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1,8))+'<Relationship Id="rId8" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/></Relationships>'

with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+''.join(content_types)+'</Types>')
    z.writestr('_rels/.rels',rels_root)
    z.writestr('ppt/presentation.xml',presentation)
    z.writestr('ppt/_rels/presentation.xml.rels',pres_rels)
    z.writestr('ppt/slideMasters/slideMaster1.xml',master_xml())
    z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels','''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>''')
    z.writestr('ppt/slideLayouts/slideLayout1.xml',layout_xml())
    z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels','''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>''')
    z.writestr('ppt/theme/theme1.xml',theme_xml())
    for i,(items,images) in enumerate(slides,1):
        rels=['''<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>''']
        if i==2:
            rels.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/workspace.png"/>')
        if i==5:
            rels.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/answer-card.png"/>')
        z.writestr(f'ppt/slides/slide{i}.xml',slide_xml(items))
        z.writestr(f'ppt/slides/_rels/slide{i}.xml.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(rels)+'</Relationships>')
    z.write(ROOT/'presentation-assets/workspace.png','ppt/media/workspace.png')
    z.write(ROOT/'presentation-assets/answer-card.png','ppt/media/answer-card.png')
print(f"Created {OUT} ({OUT.stat().st_size:,} bytes)")
