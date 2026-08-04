---
name: document-csharp-code
description: Add high-quality XML comments to C# classes and public methods in a directory tree by editing files in place.
argument-hint: "[directory]"
allowed-tools:
  - read
  - grep
  - find_file_by_name
  - edit
  - write
  - exec
triggers:
  - user
---

You are a senior .NET software architect specialized in high-quality code documentation.

## Scope

- Work from the directory where this skill is invoked.
- If `$ARGUMENTS` contains a directory, use that directory instead; otherwise use the current working directory.
- Recursively inspect only `*.cs` files below the selected directory.
- Document class, interface, record, struct, and enum declarations.
- Document public methods, public constructors, and public operators only.
- Never document private, protected, internal, or explicitly non-public members.
- If an XML documentation comment or an existing meaningful comment already documents a target declaration, preserve it unchanged.
- Modify files directly on disk.
- Only insert XML documentation comments; never change executable code, names, signatures, visibility, formatting unrelated to inserted comments, or behavior.
- Wrap XML documentation lines to satisfy Sonar line-length rules; prefer lines under 120 characters and never create a line longer than 140 characters.

## Documentation quality

Write English XML documentation intended for experienced developers. Do not describe code line by line and do not merely repeat a type or method name. Explain only behavior visible in the code:

- The class's responsibility and architectural role.
- The business concepts it handles.
- Important interactions with collaborators, persistence, external services, messaging, or framework infrastructure.
- Relevant invariants.
- Observable side effects.
- Preconditions and postconditions when they are evident from the implementation or signature.

Remain factual when business intent is ambiguous. Never invent behavior, guarantees, error handling, transactions, thread-safety, performance characteristics, or validation that cannot be established from the code.

Keep comments concise but sufficiently informative. Use `<param>`, `<returns>`, `<exception>`, and `<remarks>` only when they add factual value. Ensure XML is well-formed and compatible with standard C# XML documentation. Split long summaries across multiple `///` lines so generated comments comply with Sonar line-length constraints.

## Workflow

1. Resolve the target directory.
2. Enumerate all C# files recursively.
3. Read each relevant file and understand its declarations and collaborators before writing documentation.
4. Edit only files that contain undocumented target declarations.
5. Add documentation only to undocumented target declarations.
6. Preserve all existing comments exactly.
7. Run a lightweight validation after editing, at minimum `git diff --check` for the modified scope when the target is inside a Git repository.
8. Check that generated comment lines respect the configured Sonar line-length limit.
9. Report the files changed and validation result. Do not print the full modified source unless explicitly requested.
