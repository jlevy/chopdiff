# chopdiff API Reference

## Core Classes

### SectionNode

A node in the hierarchical section tree representing a Markdown section.

```python
@dataclass
class SectionNode:
    level: int              # 0 for root, 1-6 for headers
    title: str | None       # Header text, None for root
    start_offset: int       # Start position in original text
    end_offset: int         # End position (exclusive)
    header_end_offset: int  # End of header line
    parent: SectionNode | None = None
    children: list[SectionNode] = field(default_factory=list)
```

#### Key Methods

- `body_content: str` - Get content without the header line
- `full_content: str` - Get complete content including header
- `add_child(child: SectionNode)` - Add a child section
- `all_descendants() -> list[SectionNode]` - Get all descendant sections
- `find_by_title(title: str) -> SectionNode | None` - Find section by title
- `sections_at_level(level: int) -> list[SectionNode]` - Get sections at specific level

### SectionDoc

Parser for Markdown documents into hierarchical section structure.

```python
class SectionDoc:
    def __init__(self, text: str)
```

#### Key Properties & Methods

- `original_text: str` - The original document text
- `root_section: SectionNode` - Root node of section tree
- `all_sections() -> list[SectionNode]` - Get all sections in document order
- `sections_at_level(level: int) -> list[SectionNode]` - Get sections at level
- `find_section_by_title(title: str) -> SectionNode | None` - Find by title
- `find_section_at_offset(offset: int) -> SectionNode | None` - Find containing section

### FlexDoc

Unified interface providing lazy access to all three document views.

```python
class FlexDoc:
    def __init__(self, original_text: str)
```

#### Key Properties

- `original_text: str` - The original document text
- `text_doc: TextDoc` - Token-based view (lazy loaded)
- `text_node: TextNode` - Div-based view (lazy loaded)
- `section_doc: SectionDoc` - Section-based view (lazy loaded)

#### Navigation Methods

- `find_section_at_offset(offset: int) -> SectionNode | None`
- `find_token_at_offset(offset: int) -> int | None`
- `find_section_containing_token(token_idx: int) -> SectionNode | None`
- `section_to_token_range(section: SectionNode) -> tuple[int, int]`

#### Chunking Methods

```python
def chunk_by_sections(
    max_chunk_size: int = 2000,
    respect_levels: set[int] | None = None,
    overlap_size: int = 0
) -> list[FlexChunk]
```

Creates chunks that respect section boundaries. Parameters:
- `max_chunk_size`: Maximum characters per chunk
- `respect_levels`: Set of heading levels to keep intact (e.g., {1, 2})
- `overlap_size`: Characters to overlap between chunks

### FlexChunk

Result of section-aware chunking.

```python
@dataclass
class FlexChunk:
    start_offset: int
    end_offset: int
    sections: list[SectionNode]
    text: str
```

## Utilities

### synchronized

Thread-safety decorator for lazy loading.

```python
from chopdiff import synchronized

class MyClass:
    def __init__(self):
        self._lock = RLock()
    
    @synchronized()
    def thread_safe_method(self):
        # This method is now thread-safe
        pass
```

## Usage Patterns

### Basic Section Navigation

```python
from chopdiff import SectionDoc

doc = SectionDoc(markdown_text)

# Walk the tree
for section in doc.all_sections():
    if section.level == 2:  # Process h2 sections
        print(f"## {section.title}")
        print(section.body_content)
```

### Cross-View Operations

```python
from chopdiff import FlexDoc

doc = FlexDoc(markdown_text)

# Find token in section
section = doc.section_doc.find_section_by_title("Methods")
start_token, end_token = doc.section_to_token_range(section)
method_tokens = doc.text_doc.tokens()[start_token:end_token]
```

### Smart Document Chunking

```python
from chopdiff import FlexDoc

doc = FlexDoc(long_markdown)

# Chunk keeping h1 and h2 sections together
chunks = doc.chunk_by_sections(
    max_chunk_size=3000,
    respect_levels={1, 2},
    overlap_size=100
)

for chunk in chunks:
    # Process each chunk
    print(f"Processing {len(chunk.sections)} sections")
    process_text(chunk.text)
```