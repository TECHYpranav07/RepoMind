"""Generate comprehensive RepoMind Architecture & GraphRAG PDF Guide."""
import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx2pdf import convert


def set_cell_background(cell, fill_hex):
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner cell padding in twips (1/20th of a point)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def create_guide_document():
    doc = docx.Document()

    # Set page margins (0.75 in)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("RepoMind: Architectural Guide & Concept Manual")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 58, 138)  # Deep Navy

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Understanding Knowledge Graphs, GraphRAG, NetworkX, AST, and What-If Analysis in Simple & Technical Terms")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(12)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph()

    # Executive Callout Box
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_background(cell, "F1F5F9")
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
    p_box = cell.paragraphs[0]
    r_box_title = p_box.add_run("📌 Document Purpose:\n")
    r_box_title.bold = True
    r_box_title.font.size = Pt(10.5)
    r_box_title.font.color.rgb = RGBColor(15, 23, 42)
    r_box_text = p_box.add_run(
        "This guide explains exactly how RepoMind works under the hood. For every major concept "
        "(Knowledge Graphs, NetworkX, AST, FAISS, GraphRAG, and What-If Analysis), this document provides "
        "both a Simple Real-World Explanation (easy to grasp and explain to anyone) and a Technical Deep-Dive "
        "(exact algorithms, data structures, and implementation details)."
    )
    r_box_text.font.size = Pt(9.5)
    r_box_text.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph()

    # Helper function for Section Headers
    def add_section_header(title):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(4)
        r = h.add_run(title)
        r.font.name = "Arial"
        r.font.size = Pt(15)
        r.font.bold = True
        r.font.color.rgb = RGBColor(30, 58, 138)
        return h

    # Helper function for Comparison Tables
    def add_concept_comparison(concept_name, simple_desc, tech_desc):
        p_c = doc.add_paragraph()
        p_c.paragraph_format.space_before = Pt(8)
        p_c.paragraph_format.space_after = Pt(2)
        r_c = p_c.add_run(f"🔹 {concept_name}")
        r_c.font.bold = True
        r_c.font.size = Pt(12)
        r_c.font.color.rgb = RGBColor(15, 23, 42)

        tbl = doc.add_table(rows=2, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Headers
        cell_hdr_left = tbl.cell(0, 0)
        cell_hdr_right = tbl.cell(0, 1)
        set_cell_background(cell_hdr_left, "DBEAFE")   # Light blue
        set_cell_background(cell_hdr_right, "E0E7FF")  # Light indigo
        set_cell_margins(cell_hdr_left, top=80, bottom=80, left=120, right=120)
        set_cell_margins(cell_hdr_right, top=80, bottom=80, left=120, right=120)

        p_hl = cell_hdr_left.paragraphs[0]
        r_hl = p_hl.add_run("💡 In Simple Words (Intuitive Analogy)")
        r_hl.bold = True
        r_hl.font.size = Pt(10)
        r_hl.font.color.rgb = RGBColor(30, 58, 138)

        p_hr = cell_hdr_right.paragraphs[0]
        r_hr = p_hr.add_run("⚙️ In Technical Words (Under the Hood)")
        r_hr.bold = True
        r_hr.font.size = Pt(10)
        r_hr.font.color.rgb = RGBColor(67, 56, 202)

        # Content
        cell_body_left = tbl.cell(1, 0)
        cell_body_right = tbl.cell(1, 1)
        set_cell_background(cell_body_left, "F8FAFC")
        set_cell_background(cell_body_right, "F8FAFC")
        set_cell_margins(cell_body_left, top=100, bottom=100, left=120, right=120)
        set_cell_margins(cell_body_right, top=100, bottom=100, left=120, right=120)

        p_bl = cell_body_left.paragraphs[0]
        r_bl = p_bl.add_run(simple_desc)
        r_bl.font.size = Pt(9.5)
        r_bl.font.color.rgb = RGBColor(51, 65, 85)

        p_br = cell_body_right.paragraphs[0]
        r_br = p_br.add_run(tech_desc)
        r_br.font.size = Pt(9.5)
        r_br.font.color.rgb = RGBColor(51, 65, 85)

        doc.add_paragraph()

    # SECTION 1: WHAT IS REPOMIND?
    add_section_header("1. What is RepoMind?")
    add_concept_comparison(
        "RepoMind Overview",
        "Most AI coding assistants (like Copilot) can write or explain a single snippet of code. But they are blind to how the whole project connects together. If you change one file, they cannot tell you what else will break. RepoMind is an AI architect that understands the entire codebase as an interconnected map and predicts the exact consequences of changing any piece of software.",
        "RepoMind is an Explainable GraphRAG software intelligence system. It ingests public GitHub repositories, performs static AST analysis to construct an explicit directed multigraph (NetworkX), indexes code chunks into a dense vector index (FAISS), and couples both with a dual-hop retrieval engine to perform grounded What-If change-impact analysis and blast-radius tracing."
    )

    # SECTION 2: KNOWLEDGE GRAPH
    add_section_header("2. What is a Software Knowledge Graph?")
    add_concept_comparison(
        "Knowledge Graph",
        "Imagine a social network where people are nodes and friendships are edges. In software, a Knowledge Graph treats functions, classes, and files like people, and imports or function calls like relationships. If Class A calls Class B, there is a one-way bridge between them. This allows us to walk across the bridges to see who depends on who.",
        "A Knowledge Graph G = (V, E) is a directed labeled multigraph where vertices V represent software entities (Modules, Files, Classes, Functions, Methods, Configs, Libraries, Tests) and directed edges E represent typed semantic relationships (CONTAINS, IMPORTS, CALLS, DEPENDS_ON, IMPLEMENTS, CONFIGURES, DOCUMENTS, TESTS). Every node and edge retains metadata (source line numbers, file path, confidence, is_inferred)."
    )

    # SECTION 3: PYTHON AST
    add_section_header("3. Python AST (Abstract Syntax Tree) — The Scanner")
    add_concept_comparison(
        "Python AST",
        "Think of an AST as an X-ray scanner for code. We don't run the code or execute it (which could be dangerous or crash). Instead, Python reads the grammar of the code and breaks it down into a tree structure showing every class, function, parameter, and function call clearly.",
        "Python's standard library module `ast` parses source code into an abstract syntax tree adhering to the Python grammar grammar specification. RepoMind implements an `ASTVisitor` (subclassing `ast.NodeVisitor`) that intercepts `ast.ClassDef`, `ast.FunctionDef`, `ast.Import`, `ast.ImportFrom`, and `ast.Call` nodes to deterministically extract entity declarations and caller-callee bindings with exact line coordinates."
    )

    # SECTION 4: NETWORKX
    add_section_header("4. NetworkX — The Graph Brain")
    add_concept_comparison(
        "NetworkX",
        "NetworkX is our in-memory GPS navigation system for code. Once AST finds all the functions and calls, NetworkX stores them and lets us ask questions like: 'Starting from FAISS, what are all the paths that lead backwards to find who is calling it?' It can find shortcuts, loops, and calculate which components are the most important hubs in the system.",
        "NetworkX is a high-performance Python graph theory library. RepoMind uses `nx.DiGraph` to represent the software topology. It enables O(V + E) Breadth-First Search (BFS) traversals via `single_source_shortest_path_length`, topological sorting, in-degree/out-degree centrality calculations, cycle detection, and subgraph slicing for targeted What-If blast radius analysis."
    )

    # SECTION 5: FAISS & DENSE EMBEDDINGS
    add_section_header("5. FAISS & Vector Embeddings — The Semantic Search")
    add_concept_comparison(
        "FAISS & Embeddings",
        "Computers cannot understand English text or Python code directly, so an embedding engine translates code chunks into lists of numbers (vectors) based on their meaning. FAISS (built by Facebook AI) is a super-fast search engine that compares these lists of numbers to find the most relevant code chunks in milliseconds.",
        "FAISS (Facebook AI Similarity Search) is an indexed similarity search library. RepoMind chunks the repository using structure-aware AST boundaries, converts text to 128/256-dimensional unit-normalized dense vectors using TF-IDF + TruncatedSVD (or SentenceTransformers), and stores them in a `faiss.IndexFlatIP` index where vector inner product corresponds directly to cosine similarity."
    )

    # SECTION 6: GRAPHRAG VS STANDARD RAG
    add_section_header("6. Standard Vector RAG vs. GraphRAG vs. Hybrid GraphRAG")
    add_concept_comparison(
        "GraphRAG vs Standard RAG",
        "Standard RAG is like using Ctrl+F keyword search: if you ask 'What happens if I change FAISS?', it only finds files that literally have the word 'FAISS'. But it completely misses the API routes or pipelines that call FAISS indirectly! GraphRAG follows the actual call bridges to find everyone affected. Hybrid GraphRAG combines both: it finds the starting files using meaning, and then walks the graph bridges to find all hidden callers.",
        "Standard Vector RAG computes cosine similarity between a query vector and chunk vectors, retrieving top-k chunks. It suffers from the 'horizon problem'—failing to retrieve topologically connected components that lack lexical or semantic overlap with the prompt. Hybrid GraphRAG performs vector retrieval, extracts the identified entities into the NetworkX graph, executes a k-hop bidirectional BFS upstream and downstream, and merges both contexts for grounded synthesis."
    )

    # SECTION 7: WHAT-IF ANALYSIS ENGINE
    add_section_header("7. The What-If Analysis Engine (The Core Differentiator)")
    add_concept_comparison(
        "What-If Analysis Engine",
        "Imagine you want to replace your car's petrol engine with an electric motor. You need to know: Will the transmission fit? Will the dashboard gauges still work? What wires need to be changed? RepoMind's What-If engine does this for software. When you ask 'What if we replace FAISS with ChromaDB?', it identifies FAISS, checks every pipe connected to it, finds what breaks, identifies which tests must be rewritten, and outputs a complete risk checklist.",
        "The What-If Engine operates in 4 stages:\n1. Intent Parsing: `ChangeParser` extracts the action (`REPLACE`), target (`FAISS`), and replacement (`ChromaDB`).\n2. Neighborhood Traversal: `ImpactAnalyzer` traverses reverse edges in `nx.DiGraph` to find 1-hop direct callers (High Risk), 2-to-k hop transitive callers (Medium Risk), and linked test functions via `TESTS` edges.\n3. Subgraph Isolation: Extracts the impacted subgraph for visual rendering.\n4. Grounded Synthesis: Feeds verified paths into the LLM with strict negative constraints to prevent hallucination, generating an explainable impact report."
    )

    # SECTION 8: STEP-BY-STEP DATA FLOW
    add_section_header("8. End-to-End Data Pipeline")
    doc.add_paragraph("Here is the exact step-by-step path a repository takes through RepoMind:")

    steps = [
        ("Step 1: URL Input & Ingestion", "User provides a GitHub URL. GitHub REST API fetches README, file tree, dependencies, and code, saving them to local cache."),
        ("Step 2: Structure-Aware Chunking", "Python AST parses files into clean semantic chunks (by Class, Function, and Method) with line numbers."),
        ("Step 3: Knowledge Graph Assembly", "EntityExtractor and RelationshipExtractor build NetworkX nodes (Classes, Funcs, Libs) and edges (CALLS, IMPORTS, TESTS)."),
        ("Step 4: Vector Indexing (FAISS)", "Code chunks are converted into normalized dense vectors and stored in a local FAISS index."),
        ("Step 5: Hybrid Retrieval", "When a query arrives, FAISS finds semantic matches while NetworkX traverses caller bridges to gather full context."),
        ("Step 6: What-If Blast Radius Tracing", "For hypothetical refactorings, reverse graph BFS identifies direct callers, transitive callers, and tests."),
        ("Step 7: Interactive UI & Reports", "Streamlit displays interactive PyVis physics networks, verified citations, risk badges, and downloadable reports.")
    ]

    for title, desc in steps:
        p_step = doc.add_paragraph()
        p_step.paragraph_format.space_before = Pt(4)
        p_step.paragraph_format.space_after = Pt(2)
        r_st = p_step.add_run(f"• {title}: ")
        r_st.bold = True
        r_st.font.size = Pt(10)
        r_st.font.color.rgb = RGBColor(30, 58, 138)
        r_sd = p_step.add_run(desc)
        r_sd.font.size = Pt(9.5)
        r_sd.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph()

    # Save DOCX and convert to PDF
    docx_path = Path("RepoMind_Architecture_and_GraphRAG_Guide.docx").resolve()
    pdf_path = Path("RepoMind_Architecture_and_GraphRAG_Guide.pdf").resolve()

    doc.save(str(docx_path))
    print(f"Saved Word document to: {docx_path}")

    convert(str(docx_path), str(pdf_path))
    print(f"Successfully converted to PDF: {pdf_path}")


if __name__ == "__main__":
    create_guide_document()
