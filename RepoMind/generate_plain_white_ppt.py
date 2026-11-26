"""Generate a plain white, clean, professional presentation for RepoMind Mid-Review (40 Marks).
100% verified and strictly audited against the actual RepoMind codebase and empirical benchmark results.
Zero effects, high contrast, clean typography, selective high-value content.
"""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette (High-contrast, professional, minimalist) ───────────────────
C_BG          = RGBColor(255, 255, 255) # Pure White
C_TITLE       = RGBColor(17, 24, 39)    # Charcoal (#111827)
C_SUBTITLE    = RGBColor(75, 85, 99)    # Slate Gray (#4B5563)
C_BODY        = RGBColor(31, 41, 55)    # Dark Gray (#1F2937)
C_MUTED       = RGBColor(107, 114, 128) # Muted Gray (#6B7280)
C_PRIMARY     = RGBColor(30, 58, 138)   # Deep Navy (#1E3A8A)
C_CARD_BG     = RGBColor(255, 255, 255) # Card White
C_BORDER      = RGBColor(229, 231, 235) # Subtle Border (#E5E7EB)
C_TH_BG       = RGBColor(243, 244, 246) # Table Header (#F3F4F6)

FONT_HEADING = "Arial"
FONT_BODY    = "Calibri"


def create_presentation(output_path: str):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = C_BG

    def add_header(slide, tag: str, title: str, subtitle: str = ""):
        set_slide_background(slide)
        
        # Tag box
        tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.35))
        tf_tag = tb_tag.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = tag.upper()
        p_tag.font.name = FONT_HEADING
        p_tag.font.size = Pt(9.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = C_PRIMARY

        # Title
        tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.733), Inches(0.55))
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = C_TITLE

        # Subtitle
        if subtitle:
            tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.25), Inches(11.733), Inches(0.35))
            tf_sub = tb_sub.text_frame
            tf_sub.word_wrap = True
            tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = subtitle
            p_sub.font.name = FONT_BODY
            p_sub.font.size = Pt(11)
            p_sub.font.color.rgb = C_SUBTITLE

        # Separator rule
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.65), Inches(11.733), Inches(0.015))
        line.fill.solid()
        line.fill.fore_color.rgb = C_BORDER
        line.line.color.rgb = C_BORDER

    def add_card(slide, left, top, width, height, title: str = "", tag: str = ""):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = C_CARD_BG
        shape.line.color.rgb = C_BORDER
        shape.line.width = Pt(1)

        tx_box = slide.shapes.add_textbox(left + Inches(0.18), top + Inches(0.15), width - Inches(0.36), height - Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p0 = tf.paragraphs[0]
        if tag:
            p0.text = tag.upper()
            p0.font.name = FONT_HEADING
            p0.font.size = Pt(8.5)
            p0.font.bold = True
            p0.font.color.rgb = C_PRIMARY

            if title:
                p_title = tf.add_paragraph()
                p_title.text = title
                p_title.font.name = FONT_HEADING
                p_title.font.size = Pt(12)
                p_title.font.bold = True
                p_title.font.color.rgb = C_TITLE
                p_title.space_before = Pt(2)
        elif title:
            p0.text = title
            p0.font.name = FONT_HEADING
            p0.font.size = Pt(12)
            p0.font.bold = True
            p0.font.color.rgb = C_TITLE

        return tf

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 1: Title & Administrative Details
    # ─────────────────────────────────────────────────────────────────────────
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(0.9), Inches(10.9), Inches(0.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "MIT ACADEMY OF ENGINEERING, PUNE"
    p.font.name = FONT_HEADING
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p2 = tf.add_paragraph()
    p2.text = "Department of Electronics & Telecommunication Engineering  |  ESE Project Evaluation"
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = C_MUTED
    p2.space_before = Pt(3)

    line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(1.75), Inches(10.9), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = C_PRIMARY
    line.line.color.rgb = C_PRIMARY

    tb_main = s1.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(10.9), Inches(2.2))
    tf_main = tb_main.text_frame
    tf_main.word_wrap = True
    p = tf_main.paragraphs[0]
    p.text = "RepoMind: Explainable GraphRAG for Software Repository What-If Change-Impact Analysis"
    p.font.name = FONT_HEADING
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = C_TITLE

    p_sub = tf_main.add_paragraph()
    p_sub.text = "Mid-Review Evaluation Presentation — 40 Marks Rubric Aligned (CO1 to CO5)"
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(14)
    p_sub.font.color.rgb = C_SUBTITLE
    p_sub.space_before = Pt(8)

    p_meta = tf_main.add_paragraph()
    p_meta.text = "Course: Advanced Neural Network Architectures (2307411T)   |   Faculty Guide: Dr. Smita S. Kulkarni"
    p_meta.font.name = FONT_BODY
    p_meta.font.size = Pt(11.5)
    p_meta.font.bold = True
    p_meta.font.color.rgb = C_PRIMARY
    p_meta.space_before = Pt(10)

    card_w = Inches(3.45)
    card_gap = Inches(0.27)
    top_cards = Inches(4.7)
    card_h = Inches(1.9)

    # Card 1: Team
    tf_c1 = add_card(s1, Inches(1.2), top_cards, card_w, card_h, "Project Team", "Team Details")
    p = tf_c1.add_paragraph()
    p.text = "• Student 1: TECHYpranav07 (B.Tech E&TC)"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(4)
    p = tf_c1.add_paragraph()
    p.text = "• Student 2: Amitmali72 (B.Tech E&TC)"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p = tf_c1.add_paragraph()
    p.text = "• Domain: AI / Knowledge Graphs / Software RAG"
    p.font.size = Pt(9)
    p.font.color.rgb = C_MUTED
    p.space_before = Pt(4)

    # Card 2: Track Alignment
    tf_c2 = add_card(s1, Inches(1.2) + card_w + card_gap, top_cards, card_w, card_h, "Curriculum Alignment", "Approved Tracks")
    p = tf_c2.add_paragraph()
    p.text = "• Track 4: RAG / Domain-Specific AI"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(4)
    p = tf_c2.add_paragraph()
    p.text = "• Track 3: Generative AI / LLM Applications"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p = tf_c2.add_paragraph()
    p.text = "• Domain 8: Knowledge Systems & Graph Reasoning"
    p.font.size = Pt(9)
    p.font.color.rgb = C_MUTED
    p.space_before = Pt(4)

    # Card 3: Live Artifacts
    tf_c3 = add_card(s1, Inches(1.2) + (card_w + card_gap) * 2, top_cards, card_w, card_h, "Deliverables & Artifacts", "Verified Repository")
    p = tf_c3.add_paragraph()
    p.text = "• GitHub: github.com/TECHYpranav07/RepoMind"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(4)
    p = tf_c3.add_paragraph()
    p.text = "• Interactive UI: Streamlit (Port 8501, 5 Pages)"
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p = tf_c3.add_paragraph()
    p.text = "• Verified Tests: 11/11 Automated Tests Passing"
    p.font.size = Pt(9)
    p.font.color.rgb = C_MUTED
    p.space_before = Pt(4)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 2: Mid-Review Evaluation Rubric Matrix (40 Marks)
    # ─────────────────────────────────────────────────────────────────────────
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "ANNA 2307411T • Evaluation Matrix", "Mid-Review Evaluation Rubric — 40 Marks Breakdown",
               "Targeting the 'Excellent' standard across all 8 academic criteria mapped to Course Outcomes (CO1 to CO5).")

    t_shape = s2.shapes.add_table(9, 5, Inches(0.8), Inches(1.9), Inches(11.733), Inches(4.9))
    tbl = t_shape.table
    tbl.columns[0].width = Inches(0.6)
    tbl.columns[1].width = Inches(3.2)
    tbl.columns[2].width = Inches(0.9)
    tbl.columns[3].width = Inches(1.1)
    tbl.columns[4].width = Inches(5.933)

    rubric_rows = [
        ("S.N.", "Assessment Criterion", "Marks", "CO Mapped", "RepoMind Implementation & Verification Target"),
        ("1", "Problem Definition & Domain Relevance", "5", "CO4", "Graph-aware multi-hop code dependency & What-If blast radius analysis for microservices"),
        ("2", "Literature Survey & Research Gap", "5", "CO4", "Survey of 5 major approaches (Microsoft GraphRAG, DPR, RepoCoder, GraphCodeBERT, RAGAS)"),
        ("3", "Dataset / Knowledge Base Preparation", "5", "CO4", "Deterministic AST schema: 8 entity types, 7 edge types, curated 'ragcraft' microservice (64 nodes, 131 edges)"),
        ("4", "Optimization Strategy & Preprocessing", "5", "CO1", "ast.NodeVisitor (<120ms), FastDense SVD (256-dim), FAISS IndexFlatIP (<5ms), bounded BFS (k<=4)"),
        ("5", "Model / Architecture Selection & Justification", "5", "CO2, CO3", "Dual-Layer GraphRAG: NetworkX DiGraph + FAISS + Gemini/OpenAI + Local heuristic synthesizer fallback"),
        ("6", "Implementation Progress (Core Engine)", "10", "CO2, CO3, CO4", "100% working pipeline, 5-page Streamlit dashboard, in-memory PyVis graph, 11/11 tests pass"),
        ("7", "Preliminary Results & Experimental Plan", "3", "CO1", "Benchmarked Graph vs Hybrid on 5 questions: Recall@K, Precision@K, Impact F1, Faithfulness, Latency"),
        ("8", "Mid-Review Presentation & Viva Defense", "2", "CO5", "Live interactive demonstration, structured plain white slides, verified GitHub codebase"),
    ]

    for r_idx, row in enumerate(rubric_rows):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(9.5 if r_idx > 0 else 10)
            if r_idx == 0:
                p.font.name = FONT_HEADING
                p.font.bold = True
                p.font.color.rgb = C_PRIMARY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TH_BG
            else:
                p.font.color.rgb = C_BODY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_CARD_BG
                if c_idx in (0, 2, 3):
                    p.alignment = PP_ALIGN.CENTER
                    if c_idx == 2:
                        p.font.bold = True

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 3: Criterion 1 — Problem Definition & Domain Relevance
    # ─────────────────────────────────────────────────────────────────────────
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Rubric Criterion 1 • 5 Marks • CO4", "Criterion 1: Problem Definition & Domain Relevance",
               "Solving the fatal blindspots of flat vector RAG in software engineering and change-impact analysis.")

    c_w = Inches(3.72)
    c_gap = Inches(0.28)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    tf = add_card(s3, Inches(0.8), top_pos, c_w, card_h, "1. Real-World Engineering Problem", "Industry Challenge")
    items = [
        ("Deep Multi-Hop Dependencies", "Modern microservices have deeply nested caller/callee, import, and inheritance hierarchies spanning multiple files and packages."),
        ("Vector RAG Blindspot", "Traditional RAG treats code like flat prose. Arbitrary token/line chunking slices through classes and functions, completely discarding AST syntactic scope."),
        ("Silent Breaking Changes", "A developer modifies a function signature or removes a cache key, unaware that downstream services 3-4 hops away will silently break in production."),
        ("LLM Hallucinations in Code", "Standard LLM assistants lack access to structural call graphs, frequently inventing non-existent method signatures or missing transitive callers.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    tf = add_card(s3, Inches(0.8) + c_w + c_gap, top_pos, c_w, card_h, "2. Domain Relevance & Target Users", "Domain Fit")
    items = [
        ("Curriculum Alignment", "Directly addresses Track 4 (RAG / Domain-Specific AI), Track 3 (Generative AI / LLM), and Domain 8 (Knowledge Systems)."),
        ("Primary Stakeholders", "Software Architects, Senior Backend Engineers, QA Test Leads, and DevOps / Release Managers reviewing Pull Requests."),
        ("Industrial Use-Case 1", "Automated Pull Request Risk Auditing: Simulates the exact blast radius before merging code into main branches."),
        ("Industrial Use-Case 2", "Architectural Refactoring Advisor: Replaces trial-and-error migration with evidence-grounded dependency impact analysis.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    tf = add_card(s3, Inches(0.8) + (c_w + c_gap) * 2, top_pos, c_w, card_h, "3. Measurable Technical Objectives", "Target Goals")
    items = [
        ("Deterministic AST Extraction", "100% deterministic AST parsing of 8 entity types and 7 relational edge types without relying on LLM heuristics."),
        ("Multi-Hop Blast Radius Speed", "Sub-50ms upstream/downstream dependency traversal via bounded BFS on NetworkX DiGraph."),
        ("Explainable What-If Engine", "Automated risk scoring (Critical, High, Medium, Low) based on caller count, test coverage, and config links."),
        ("Verifiable Source Grounding", "Zero hallucinated methods: every generated recommendation provides exact file paths, line ranges, and traversed AST paths.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 4: Criterion 2 — Literature Survey & Research Gaps
    # ─────────────────────────────────────────────────────────────────────────
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Rubric Criterion 2 • 5 Marks • CO4", "Criterion 2: Literature Survey & Identified Research Gaps",
               "Evaluating related state-of-the-art methods and identifying the structural gap addressed by RepoMind.")

    t_shape = s4.shapes.add_table(6, 4, Inches(0.8), Inches(1.9), Inches(11.733), Inches(3.3))
    tbl = t_shape.table
    tbl.columns[0].width = Inches(2.7)
    tbl.columns[1].width = Inches(2.6)
    tbl.columns[2].width = Inches(2.8)
    tbl.columns[3].width = Inches(3.633)

    lit_rows = [
        ("Paper / Approach", "Methodology Used", "Key Strength", "Identified Limitation / Gap"),
        ("Microsoft GraphRAG\n(Edge et al., 2024)", "LLM-extracted entity graphs & Leiden community clustering", "High-level global thematic document summaries", "Extremely expensive LLM extraction passes; heuristic and noisy for exact code syntax"),
        ("Dense Passage Retrieval\n(DPR, Karpukhin et al., 2020)", "Dual-encoder semantic embeddings with dot-product search", "Fast semantic vector search across large corpora", "Zero structural awareness; cannot trace multi-hop caller chains or class hierarchies"),
        ("RepoCoder\n(Zhang et al., 2023)", "Iterative retrieval-augmented code generation pipeline", "Refines code completions through iterative context retrieval", "Lacks formal graph traversal, topological blast radius, and What-If impact simulation"),
        ("GraphCodeBERT\n(Guo et al., 2021)", "Pre-trained transformer with data-flow and variable-flow edges", "Understands semantic relationships and data flow in code", "Opaque neural embeddings; lacks explainable path extraction and interactive refactoring advice"),
        ("RAGAS Framework\n(Es et al., 2023)", "Automated LLM-as-a-judge metric evaluation framework", "Standardized Faithfulness, Answer Relevance, and Context Recall", "Designed strictly for prose text QA; does not measure code graph traversal or impact accuracy")
    ]

    for r_idx, row in enumerate(lit_rows):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(9)
            if r_idx == 0:
                p.font.name = FONT_HEADING
                p.font.bold = True
                p.font.color.rgb = C_PRIMARY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TH_BG
            else:
                p.font.color.rgb = C_BODY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_CARD_BG

    tf = add_card(s4, Inches(0.8), Inches(5.4), Inches(11.733), Inches(1.5), "The Core Research Gap & RepoMind's Novel Contribution", "Gap Closure")
    p = tf.add_paragraph()
    p.text = "• The Fundamental Gap: Pure static analyzers (AST / LSP / ctags) understand syntax but cannot explain risks or perform generative reasoning in natural language. Conversely, pure LLM / vector RAG systems reason fluently but hallucinate non-existent callers and miss transitive dependencies."
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(4)

    p = tf.add_paragraph()
    p.text = "• RepoMind Novelty: A Dual-Layer Hybrid GraphRAG uniting deterministic AST Knowledge Graphs (NetworkX) with dense semantic search (FAISS IndexFlatIP) to achieve mathematically verifiable multi-hop blast radius tracing and evidence-grounded What-If synthesis."
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p.space_before = Pt(3)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 5: Criterion 3 — Knowledge Base & AST Schema
    # ─────────────────────────────────────────────────────────────────────────
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Rubric Criterion 3 • 5 Marks • CO4", "Criterion 3: Dataset / Knowledge Base Preparation & Schema",
               "Deterministic multi-source ingestion pipeline and formal software knowledge graph schema.")

    c_w = Inches(3.72)
    c_gap = Inches(0.28)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    # Col 1: Ingestion Pipeline
    tf = add_card(s5, Inches(0.8), top_pos, c_w, card_h, "1. Ingestion & Preprocessing", "Multi-Source Input")
    items = [
        ("Multi-Source Ingestion", "Accepts live GitHub repository URLs (REST API with tree streaming & rate-limit handling) or local repository directories."),
        ("Curated 'ragcraft' Testbed", "Includes reference architecture: 11 files, realistic FastAPI microservice with authentication, cache, vector store, pipeline, and test suites."),
        ("Codebase Metrics on Testbed", "Extracts 64 knowledge graph nodes and 131 relational edges; tracks exact start_line, end_line, and line_count."),
        ("File Scope Filters", "Recursively processes .py (code), .md (docs), .toml/.yaml/.cfg (configs), and requirements.txt; skips build artifacts (.git, __pycache__, .venv).")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # Col 2: 8 Entity Types
    tf = add_card(s5, Inches(0.8) + c_w + c_gap, top_pos, c_w, card_h, "2. 8 Typed Graph Entities", "AST Entity Schema")
    entities = [
        ("Repository", "Root node storing owner, repo name, stars, default branch, language."),
        ("File", "Source files, documentation, configs, and dependency manifests."),
        ("Class", "AST class declarations, docstrings, line ranges, and base classes."),
        ("Function", "Standalone functions, class methods (Class.method), and async coroutines."),
        ("Library", "Third-party dependencies parsed from requirements.txt and pyproject.toml."),
        ("Configuration", "Environment and build settings (.toml, .yaml, .cfg, .ini, setup.py)."),
        ("Documentation", "Markdown section headings and architectural documentation blocks."),
        ("Test", "Pytest test functions (test_*) and test suites covering target symbols.")
    ]
    for e_name, e_desc in entities:
        p = tf.add_paragraph()
        p.text = f"• {e_name}: {e_desc}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(4)

    # Col 3: 7 Relational Edge Types
    tf = add_card(s5, Inches(0.8) + (c_w + c_gap) * 2, top_pos, c_w, card_h, "3. 7 Relational Edge Types", "Graph Relationships")
    edges = [
        ("CONTAINS", "Hierarchy edge: Repository -> File, File -> Class/Function, Class -> Method."),
        ("IMPORTS", "Module binding: File -> Library, File -> Imported internal classes/functions."),
        ("CALLS", "Invocation edge: Function/Method -> Callee function/method or class constructor."),
        ("DEPENDS_ON", "Subsystem dependency: Repo -> Library, Module -> Subsystem."),
        ("IMPLEMENTS", "OOP Inheritance: Class -> Base Class identified via AST node.bases."),
        ("TESTS", "Verification link: Test function -> Target class/method under test."),
        ("DOCUMENTS", "Provenance edge: Markdown doc section -> Mentioned code entity.")
    ]
    for ed_name, ed_desc in edges:
        p = tf.add_paragraph()
        p.text = f"• {ed_name}: {ed_desc}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 6: Criterion 4 — Optimization Strategy & Preprocessing
    # ─────────────────────────────────────────────────────────────────────────
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Rubric Criterion 4 • 5 Marks • CO1", "Criterion 4: Optimization Strategy & Preprocessing Design",
               "Architectural optimizations ensuring sub-millisecond execution, zero cloud dependency, and low memory overhead.")

    c_w = Inches(5.72)
    c_gap = Inches(0.28)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    # Left Card
    tf = add_card(s6, Inches(0.8), top_pos, c_w, card_h, "1. Deterministic AST & Graph Traversal Optimizations", "Structural Computation")
    items = [
        ("Zero-Cost Native AST Visitor", "Uses Python's built-in ast.NodeVisitor. Parses files into complete syntax trees in <120 ms without expensive LLM extraction passes or heavy external compilers."),
        ("Structure-Aware Chunking", "StructureAwareChunker chunks code along natural class and method boundaries rather than fixed token lengths, preserving docstrings and complete code blocks."),
        ("Inverted Graph Indexing", "Pre-computes graph.reverse() during ingestion. Enables instant upstream caller traversal without scanning all graph edges at query time."),
        ("Bounded BFS Search (Depth Cutoff k <= 4)", "Restricts upstream/downstream impact searches to depth k with max_nodes capping to guarantee traversal finishes in <50 ms and prevent combinatorial explosion."),
        ("In-Memory PyVis Network Generation", "Generates interactive physics graph HTML directly in memory via net.generate_html(), avoiding disk I/O bottlenecks and Windows file-lock errors.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # Right Card
    tf = add_card(s6, Inches(0.8) + c_w + c_gap, top_pos, c_w, card_h, "2. Neural Computation & Vector Search Optimizations", "Vector Store Optimization")
    items = [
        ("FastDense SVD Embeddings (256-dim)", "FastDenseEmbeddingEngine combines TF-IDF vocabulary with TruncatedSVD dimensionality reduction (256 dimensions) + L2 normalization. Executes in <1 ms on pure CPU with 0 external dependencies."),
        ("FAISS IndexFlatIP Cosine Search", "Uses FAISS IndexFlatIP (Inner Product on L2-normalized vectors). Delivers mathematically exact Cosine Similarity matching in <5 ms across repository chunks."),
        ("Pluggable Neural Backends", "Seamlessly supports SentenceTransformers (all-MiniLM-L6-v2) or cloud API embeddings when GPU or semantic depth is preferred."),
        ("Monotonically Unique Citation Tracking", "ContextBuilder ensures non-colliding citation identifiers [Source 1..N] between graph nodes and vector chunks, eliminating citation cross-talk."),
        ("Local Heuristic Synthesizer (Zero-Key Fallback)", "Guarantees 100% platform availability: if Gemini or OpenAI API keys are absent or rate-limited, local grounded engine synthesizes answers from verified AST paths.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}: {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 7: Criterion 5 — Dual-Layer Hybrid GraphRAG Architecture
    # ─────────────────────────────────────────────────────────────────────────
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Rubric Criterion 5 • 5 Marks • CO2, CO3", "Criterion 5: Model & System Architecture Selection",
               "End-to-end dataflow combining deterministic AST graph traversal with dense semantic retrieval.")

    f_w = Inches(2.78)
    f_gap = Inches(0.2)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    # Step 1: Ingestion & Parsing
    tf = add_card(s7, Inches(0.8), top_pos, f_w, card_h, "Stage 1: Parsing", "Ingestion Layer")
    items = [
        ("Input Sources", "GitHub repository URL (REST API) or local repository directory."),
        ("Structure Chunker", "Splits into class/method chunks with line number metadata."),
        ("AST Visitor", "Extracts 8 entity types and 7 relational edge types deterministically.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # Step 2: Dual Indexing
    tf = add_card(s7, Inches(0.8) + (f_w + f_gap), top_pos, f_w, card_h, "Stage 2: Indexing", "Dual Knowledge Store")
    items = [
        ("NetworkX DiGraph", "Stores code entities as typed nodes and dependencies as directed edges."),
        ("FastDense SVD", "Embeds chunk text into 256-dim dense representations on CPU."),
        ("FAISS IndexFlatIP", "Maintains vector index for exact cosine nearest-neighbor search.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # Step 3: Hybrid Retrieval
    tf = add_card(s7, Inches(0.8) + (f_w + f_gap) * 2, top_pos, f_w, card_h, "Stage 3: Retrieval", "Hybrid Coordinator")
    items = [
        ("Vector Search", "Retrieves top-k semantically relevant chunks for conceptual queries."),
        ("Graph Entity Resolution", "Resolves query terms and top-chunk symbols to graph nodes."),
        ("k-Hop BFS Traversal", "Extracts connected subgraphs up to depth k around resolved entities."),
        ("Context Builder", "Merges vector source snippets with explicit relationship paths.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # Step 4: Grounded Synthesis
    tf = add_card(s7, Inches(0.8) + (f_w + f_gap) * 3, top_pos, f_w, card_h, "Stage 4: Synthesis", "LLM Reasoning")
    items = [
        ("Grounded Prompting", "Injects verified source snippets and exact graph paths into LLM."),
        ("Multi-Model Support", "Google Gemini 2.5 Flash, OpenAI GPT-4o-mini, or Local Engine."),
        ("Verifiable Output", "Generates answers citing exact files, line numbers, and causal paths."),
        ("Zero Hallucination", "Strict system prompt restricts LLM to provided evidence.")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 8: Criterion 6 — What-If Change-Impact Engine
    # ─────────────────────────────────────────────────────────────────────────
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Rubric Criterion 6 • 10 Marks • Core Differentiator", "Criterion 6: What-If Change-Impact Analysis Engine",
               "Predicting the blast radius of hypothetical code changes before committing to production.")

    c_w = Inches(5.72)
    c_gap = Inches(0.28)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    # Left Card
    tf = add_card(s8, Inches(0.8), top_pos, c_w, card_h, "1. Change-Impact Pipeline & Algorithms", "Impact Engine Logic")
    items = [
        ("ChangeParser (Natural Language to Entity)", "Parses natural language refactoring intent (Replace, Remove, Modify, Upgrade, Add) and extracts target entities. Uses token decomposition, stemming ('caching' -> 'cache'), and weighted scoring to resolve graph nodes (e.g. 'Redis caching' -> RedisCache)."),
        ("ImpactAnalyzer (Multi-Hop Reverse BFS)", "Performs reverse BFS traversal on reversed_graph from target node(s) up to depth k:\n  • 1-Hop: Identifies direct callers, importers, and consumers.\n  • 2..k Hops: Recursively traces transitive downstream dependencies.\n  • Path Deduplication: Uniquely indexes dependency paths by (from, to, relation)."),
        ("Automated Multi-Factor Risk Scoring", "Classifies refactoring risk based on topological impact:\n  • High Risk: Total affected > 6 components, or >= 3 direct callers, or >= 3 broken test suites.\n  • Medium Risk: Total affected >= 2 components or >= 1 test suite.\n  • Low Risk: Isolated leaf components with 0-1 callers."),
        ("WhatIfReportCoordinator (Synthesis & Export)", "Synthesizes an 8-section report with mitigation recommendations; exports to downloadable Markdown (.md) and structured JSON (.json).")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(5)

    # Right Card: Real-World Example
    tf = add_card(s8, Inches(0.8) + c_w + c_gap, top_pos, c_w, card_h, "2. Real-World Walkthrough: 'What if we remove Redis caching?'", "Empirical Execution")
    items = [
        ("Hypothetical Change Input", "'What if we remove Redis caching?'"),
        ("Resolved Target Entities", "class:ragcraft/storage/cache.py:RedisCache, lib:redis, and member methods (RedisCache.get, RedisCache.set)."),
        ("Direct Affected Components (1-Hop)", "• SemanticRetriever.__init__ in ragcraft/retrieval/retriever.py\n• requirements.txt (direct library dependency)\n• ragcraft/storage/cache.py (module container)"),
        ("Transitive Inferred Impacts (2-Hop)", "• SemanticRetriever.retrieve (downstream retrieval pipeline)\n• ragcraft/pipeline/rag_pipeline.py: RAGPipeline orchestrator"),
        ("Test Suites Requiring Updates", "• tests/test_retriever.py: test_retriever_query_caching (directly calls RedisCache through SemanticRetriever)"),
        ("Evaluated Risk Level", "HIGH RISK (Direct callers detected, broken test suite identified, storage contract altered).")
    ]
    for h_txt, b_txt in items:
        p = tf.add_paragraph()
        p.text = f"• {h_txt}:\n  {b_txt}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(5)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 9: Criterion 6 — Implementation Progress & Web Application
    # ─────────────────────────────────────────────────────────────────────────
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Rubric Criterion 6 • 10 Marks • CO2, CO3, CO4", "Criterion 6: Implementation Progress — Complete Working System",
               "100% operational Streamlit web platform featuring 5 interactive modules and 11/11 passing tests.")

    m_w = Inches(2.2)
    m_gap = Inches(0.18)
    top_pos = Inches(1.9)
    card_h = Inches(4.0)

    modules = [
        ("Module 1", "Home / Dashboard", [
            "GitHub & local repo ingestion",
            "Indexed files & chunk metrics",
            "Entity & edge distribution",
            "Session isolation on repo switch"
        ]),
        ("Module 2", "Repository Explorer", [
            "In-memory PyVis physics graph",
            "Entity type multi-filtering",
            "Interactive node detail inspector",
            "Source code & syntax viewer"
        ]),
        ("Module 3", "Repository Chat", [
            "Hybrid, Graph, & Vector modes",
            "Dynamic suggested questions",
            "Provenance citations with lines",
            "Persistent model & latency tags"
        ]),
        ("Module 4", "What-If Analysis", [
            "Natural language refactoring input",
            "Upstream blast radius tracing",
            "Affected component inventory",
            "Markdown & JSON export"
        ]),
        ("Module 5", "Evaluation Suite", [
            "GraphRAG vs Hybrid comparison",
            "4 large KPI summary cards",
            "4 separate grouped bar charts",
            "CSV export & metric glossary"
        ])
    ]

    for idx, (m_tag, m_title, m_items) in enumerate(modules):
        tf = add_card(s9, Inches(0.8) + (m_w + m_gap) * idx, top_pos, m_w, card_h, m_title, m_tag)
        for item in m_items:
            p = tf.add_paragraph()
            p.text = f"• {item}"
            p.font.name = FONT_BODY
            p.font.size = Pt(8.8)
            p.font.color.rgb = C_BODY
            p.space_before = Pt(5)

    kpi_w = Inches(2.78)
    kpi_gap = Inches(0.2)
    kpi_top = Inches(6.05)
    kpi_h = Inches(1.05)

    kpi_data = [
        ("100% Functional", "End-to-End Pipeline Operational"),
        ("11 / 11 Passed", "Automated PyTest Test Suite"),
        ("0 File Locks", "In-Memory PyVis HTML Rendering"),
        ("< 50 ms", "Average Graph Traversal Latency")
    ]
    for idx, (k_val, k_lbl) in enumerate(kpi_data):
        tf = add_card(s9, Inches(0.8) + (kpi_w + kpi_gap) * idx, kpi_top, kpi_w, kpi_h)
        p = tf.paragraphs[0]
        p.text = k_val
        p.font.name = FONT_HEADING
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY
        p.alignment = PP_ALIGN.CENTER

        p2 = tf.add_paragraph()
        p2.text = k_lbl
        p2.font.name = FONT_BODY
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = C_MUTED
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(2)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 10: Criterion 7 — Empirical Benchmarking & Comparative Results
    # ─────────────────────────────────────────────────────────────────────────
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Rubric Criterion 7 • 3 Marks • CO1", "Criterion 7: Preliminary Experimental Results & Evaluation",
               "Actual empirical benchmark comparing GraphRAG vs Hybrid GraphRAG on the 5-question BENCHMARK_DATASET.")

    t_shape = s10.shapes.add_table(7, 5, Inches(0.8), Inches(1.9), Inches(11.733), Inches(3.4))
    tbl = t_shape.table
    tbl.columns[0].width = Inches(2.8)
    tbl.columns[1].width = Inches(1.7)
    tbl.columns[2].width = Inches(1.7)
    tbl.columns[3].width = Inches(1.5)
    tbl.columns[4].width = Inches(4.033)

    eval_rows = [
        ("Evaluation Metric", "GraphRAG (AST)", "Hybrid GraphRAG", "Difference", "Engineering Interpretation"),
        ("Retrieval Recall@K", "50.0 %", "58.3 %", "+ 8.3 % (Hybrid)", "Semantic vectors discover relevant files that lack explicit keyword/AST matches."),
        ("Retrieval Precision@K", "45.0 %", "55.0 %", "+ 10.0 % (Hybrid)", "Combining vector similarity with graph connectivity filters out irrelevant snippets."),
        ("Impact Detection F1", "23.7 %", "38.9 %", "+ 15.2 % (Hybrid)", "Hybrid captures both structurally connected callers and semantically related tests."),
        ("Answer Correctness", "9.3 %", "7.7 %", "- 1.6 % (Graph)", "Token-level F1 against reference answers using the local heuristic synthesizer."),
        ("Faithfulness (Lexical)", "35.3 %", "17.6 %", "+ 17.7 % (Graph)", "Pure Graph context is highly concise; larger Hybrid context lowers lexical token overlap."),
        ("Average Latency", "6.4 ms", "5.7 ms", "0.7 ms difference", "Both methods execute in sub-10ms; hybrid vector lookup prunes search space efficiently.")
    ]

    for r_idx, row in enumerate(eval_rows):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(9)
            if r_idx == 0:
                p.font.name = FONT_HEADING
                p.font.bold = True
                p.font.color.rgb = C_PRIMARY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TH_BG
            else:
                p.font.color.rgb = C_BODY
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_CARD_BG
                if c_idx in (1, 2, 3):
                    p.alignment = PP_ALIGN.CENTER
                    if c_idx == 3:
                        p.font.bold = True

    tf = add_card(s10, Inches(0.8), Inches(5.45), Inches(11.733), Inches(1.45), "Key Experimental Findings & Engineering Trade-Offs", "Empirical Insights")
    p = tf.add_paragraph()
    p.text = "• Retrieval Superiority of Hybrid GraphRAG (+8.3% Recall, +10.0% Precision): Hybrid retrieval achieves higher recall and precision by bridging natural language developer queries and formal symbol names, ensuring connected modules are retrieved even when terminology differs."
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(3)

    p = tf.add_paragraph()
    p.text = "• Grounding Trade-Off (+17.7% Graph Faithfulness): Pure GraphRAG achieves higher lexical faithfulness because its context contains exclusively verified AST paths. Hybrid RAG introduces broader semantic context, requiring careful prompt synthesis to maximize factual precision."
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.color.rgb = C_BODY
    p.space_before = Pt(3)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 11: Future Scope & End-Semester Roadmap
    # ─────────────────────────────────────────────────────────────────────────
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Rubric Criterion 7 • Future Work & ESE Readiness", "Experimental Plan & Roadmap for End-Semester Exam (50 Marks)",
               "Structured milestones to transition RepoMind from mid-review prototype to production-grade platform.")

    c_w = Inches(2.78)
    c_gap = Inches(0.2)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    phases = [
        ("Phase 1", "Multi-Language AST", "End-Sem Week 2", [
            "Tree-Sitter Parser: Extend deterministic AST parsing from Python to TypeScript, Java, and Go.",
            "Polyglot Microservices: Trace cross-boundary calls across REST and gRPC interfaces.",
            "Global Symbol Table: Cross-file symbol resolution across multiple repositories."
        ]),
        ("Phase 2", "Large-Scale Benchmark", "End-Sem Week 4", [
            "Open-Source Corpora: Evaluate on repositories >50k LOC (FastAPI, Flask, Requests, Click).",
            "Memory Stress Testing: Benchmark FAISS index scaling and graph memory on 500+ files.",
            "100-Question Dataset: Expand ground-truth What-If evaluation dataset with human verification."
        ]),
        ("Phase 3", "GitHub CI/CD Bot", "End-Sem Week 6", [
            "GitHub Action: Package RepoMind as an automated pull-request review bot.",
            "Automated PR Comments: Post What-If blast radius reports directly on GitHub PRs.",
            "Pre-Merge Guardrail: Block merges when high-risk architectural regressions are detected."
        ]),
        ("Phase 4", "Research Paper", "Final Defense", [
            "Conference Submission: Format paper for IEEE / Springer student AI track.",
            "Ablation Studies: Comprehensive empirical evaluation: Pure Graph vs Vector vs Hybrid.",
            "Open Source Release: Publish package and documentation on PyPI and GitHub."
        ])
    ]

    for idx, (p_tag, p_title, p_time, p_items) in enumerate(phases):
        tf = add_card(s11, Inches(0.8) + (c_w + c_gap) * idx, top_pos, c_w, card_h, p_title, p_tag)
        p = tf.add_paragraph()
        p.text = f"Target: {p_time}"
        p.font.name = FONT_HEADING
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY
        p.space_before = Pt(2)

        for item in p_items:
            p = tf.add_paragraph()
            p.text = f"• {item}"
            p.font.name = FONT_BODY
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_BODY
            p.space_before = Pt(6)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 12: Criterion 8 — Viva Defense & Rubric Compliance Checklist
    # ─────────────────────────────────────────────────────────────────────────
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Rubric Criterion 8 • 2 Marks • CO5", "Criterion 8: Mid-Review Viva & Rubric Compliance Checklist",
               "Systematic verification of all 8 assessment criteria against the 40-mark evaluation rubric.")

    c_w = Inches(5.72)
    c_gap = Inches(0.28)
    top_pos = Inches(1.9)
    card_h = Inches(5.0)

    tf = add_card(s12, Inches(0.8), top_pos, c_w, card_h, "1. Rubric Compliance Verification (40/40 Marks)", "Rubric Checklist")
    checklist = [
        ("Criterion 1 (5 Marks | CO4)", "Clear problem formulation, domain relevance (Track 4/3), and measurable objectives defined."),
        ("Criterion 2 (5 Marks | CO4)", "Survey of 5 major approaches; identified vector RAG structural gap; justified GraphRAG."),
        ("Criterion 3 (5 Marks | CO4)", "8 AST entity types, 7 edge types, and curated 'ragcraft' microservice (64 nodes, 131 edges) verified."),
        ("Criterion 4 (5 Marks | CO1)", "Optimization: Fast AST visitor (<120ms), FastDense SVD, FAISS IndexFlatIP (<5ms), bounded BFS."),
        ("Criterion 5 (5 Marks | CO2, CO3)", "Dual-layer GraphRAG architecture technically justified with clear multi-stage dataflow."),
        ("Criterion 6 (10 Marks | CO2-4)", "100% functional pipeline, 5-page Streamlit dashboard, in-memory PyVis graph, 11/11 tests pass."),
        ("Criterion 7 (3 Marks | CO1)", "Actual empirical evaluation on 5 questions; clear roadmap for End-Semester exam (50 Marks)."),
        ("Criterion 8 (2 Marks | CO5)", "Professional plain white presentation, confident viva defense, and live application demo.")
    ]
    for c_title, c_desc in checklist:
        p = tf.add_paragraph()
        p.text = f"• ✓ {c_title}: {c_desc}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(4)

    tf = add_card(s12, Inches(0.8) + c_w + c_gap, top_pos, c_w, card_h, "2. Project Artifacts & Viva Defense Readiness", "Verified Artifacts")
    artifacts = [
        ("GitHub Repository", "https://github.com/TECHYpranav07/RepoMind (all latest commits synchronized)."),
        ("Live Web Application", "Streamlit running locally on http://localhost:8501 (instant demonstration ready)."),
        ("Automated Test Suite", "Run 'python repomind/tests/test_all_components.py' -> 11/11 tests pass (100% pass rate)."),
        ("Documentation Artifacts", "Complete architecture guide, PDF documentation, and rubric alignment matrix."),
        ("Course Outcome Mapping", "  • CO1: Optimization & performance (FastDense, FAISS, bounded BFS)\n  • CO2 & CO3: Deep learning, vector retrieval & LLM generation\n  • CO4: Engineering problem formulation & dataset preparation\n  • CO5: Professional presentation, viva defense & technical ethics")
    ]
    for a_title, a_desc in artifacts:
        p = tf.add_paragraph()
        p.text = f"• {a_title}: {a_desc}"
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_BODY
        p.space_before = Pt(6)

    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")


if __name__ == "__main__":
    out_file = "RepoMind_Mid_Review_Presentation_Plain_White.pptx"
    if len(sys.argv) > 1:
        out_file = sys.argv[1]
    create_presentation(out_file)
