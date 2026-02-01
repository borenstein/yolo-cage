# CLAUDE.md

<!-- Copyright (c) 2026 David Bruce Borenstein. All Rights Reserved. -->

This document encodes how I want software built. It is the invariant layer—enduring philosophy that stays forever. Work items and acceptance criteria live in GitHub Issues.

---

## Version Control Discipline

**Version control is strictly for artifacts with lasting value.** Every committed file—code, documentation, configuration—must remain useful throughout that artifact's lifecycle.

Never commit:
- Status updates or progress reports directed at the operator at time of commit
- Ephemeral analysis documents that become stale once acted upon
- Issue numbers, story names, or PR links in comments (these become meaningless noise)
- "Implementation complete" summaries or similar operator-facing messages

The code is the source of truth. If something is implemented, the code shows it. If something is documented, it belongs in docs/ or comments that explain *why*, not *what was done when*.

---

## Ubiquitous Language

Domain terminology is the foundation of codebase clarity. When the code speaks the same language as the domain, new agents can orient themselves quickly, and subtle bugs reveal themselves as obvious contradictions.

**Resolve naming confusion before writing code.** If a concept feels awkward to name, that's a signal the domain model needs refinement. Stop and discuss. A term that requires explanation is a term that will cause confusion later.

The [glossary](docs/glossary.md) defines the project's ubiquitous language. Use it. Extend it when new concepts emerge. Every PR should leave the language clearer than it found it.

**Smells:**
- "Synthetic" concepts—implementation details leaking into domain language
- Bundled parameter objects that nobody would ever say aloud
- Multiple terms for the same concept, or one term used inconsistently

---

## Architecture

### Hierarchy of Single Responsibilities

Each module has one job, defined in terms of the systems it delegates to. How it accomplishes that job is its own business. Parent modules don't reach into children's internals; children don't know about their grandparents.

This enables scaling because you only need to hold a few ancestors and your direct children in your head at once.

### Loose Coupling, Tight Boundaries

Modules communicate through well-defined types. These types are the contracts. Internals can change without rippling outward.

---

## Code

### Naming

Names should hit you over the head. Code should read literately. If you need a comment to explain what something does, the name is wrong.

- Full words: `instance` not `inst`, `configuration` not `cfg`
- Names can be long if clarity demands it
- Align with domain terminology from the glossary
- Function names must be grammatically valid: `list_sandboxes` not `sandbox_list`

### Comments

Almost none. Comments exist only for things that genuinely cannot be encoded in the code—usually "why" explanations for non-obvious decisions.

- Tests reveal the "what"
- Code reveals the "how"
- Architecture reveals the "to what end"

### Error Handling

Three tiers:

1. **Validation errors:** Fail fast at boundaries. Bad input never penetrates past the types.
2. **Expected failure modes:** Structured results or clear error messages, not silent failures.
3. **Programmer errors:** Exceptions. Don't handle gracefully—it's a bug.

### Dependencies

Add dependencies when they earn their place. Don't add them speculatively.

---

## Testing

### Tests as Specification

Tests exist to **specify contracts**. A test declares: "This unit promises X." The test name states the promise in domain language. The test body constructs inputs, calls the unit, and verifies the promise holds.

If you can't articulate the core tests, you're not ready to write code. The tests are the promise; the code fulfills it.

**Good test names read as contracts:**
- `test_resolve_single_instance` — the contract is that a single instance is auto-selected
- `test_delete_clears_default` — the contract is that deleting the default instance clears the default
- `test_migrate_legacy_preserves_config` — the contract is that migration doesn't lose data

**Bad test names describe mechanics:**
- `test_function_returns_correct_value` — what's "correct"?
- `test_it_works` — what does "works" mean?

### No Testing Theater

Don't test every getter. Don't test implementation details. Don't generate trivial assertions to hit coverage numbers. Don't invent improbable edge cases to appear thorough.

**The standard:** What would someone write if they had time, planned to hand off the project, and wanted it to stay maintainable?

### Unit Tests Enable Clarity

Functional code takes explicit dependencies. When functions don't reach into global state, you can construct minimal inputs directly. No mocking frameworks needed.

If testing a function requires elaborate setup, that's a design smell. Fix the design, don't paper over it with test infrastructure.

---

## Human-AI Collaboration

### Documents as Consensus Layer

Both of us are unreliable—but that's a feature. The tension between our different failure modes surfaces insights that neither would reach alone. Documents (CLAUDE.md, glossary, architecture docs) are the synthesis we refer back to when we've drifted.

Pre-code planning surfaces mistakes before they're encoded. Invest in it.

### Division of Labor

**Human:** Architectural decisions, "why" and "to what end," judgment on scope, final approval, merging PRs.

**AI:** Tracking detailed state, correlating specifics across the codebase, generating conforming implementation, catching inconsistencies, creating PRs for review.

### Red Flags

Watch for patterns that signal AI slop:
- Deep nesting where flat structure would do
- Premature abstraction or over-engineering
- Test data that doesn't actually test what it claims
- Related functions scattered apart instead of grouped together
- Monolithic files that should be factored into focused modules

### What Lives Where

- **CLAUDE.md:** Enduring philosophy. Stays forever.
- **GitHub Issues:** Work tracking. Tasks, bugs, feature requests.
- **docs/:** Domain models, architecture, glossary. Specifications, not tracking artifacts.
- **Code:** System of record. Self-documenting via tests, types, naming.

---

## Development

See [README.md](README.md) for setup instructions and [docs/glossary.md](docs/glossary.md) for terminology.

### Prerequisites

- Vagrant with libvirt (Linux) or QEMU (macOS)
- 8GB RAM, 4 CPUs available for the [Runtime](docs/glossary.md#runtime)

### Testing Changes

```bash
# Run tests
source venv/bin/activate
pytest tests/ -v

# Test CLI
./scripts/yolo-cage --help
./scripts/yolo-cage instances
./scripts/yolo-cage status
```

### CI Requirements

The main branch must always build successfully:
1. `vagrant up` completes without errors
2. All tests pass
3. CLI commands work as documented
