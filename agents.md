# Agent Guidelines

This document provides essential guidelines for AI agents working on this codebase.

## Primary Reference: Game Specification

**ALWAYS refer to `CLONE_WARS_WAR_SIM_MVP.md` for the complete game specification and design requirements.**

This markdown document is the **source of truth** for:
- MVP scope and constraints
- Game mechanics and systems
- Implementation requirements
- Acceptance criteria
- Design decisions

Before making any changes that affect game logic, UI, or core systems, **read and understand the relevant sections** of `CLONE_WARS_WAR_SIM_MVP.md`.

## Always Use Todos

**You MUST use the todo system for any task that involves:**
- Multiple steps or changes
- Complex modifications
- Feature implementations
- Refactoring work
- Bug fixes that require investigation

### Todo Best Practices:
1. **Break down complex tasks** into specific, actionable todo items
2. **Mark todos as in_progress** when you start working on them
3. **Mark todos as completed** immediately after finishing each item
4. **Only one todo should be in_progress at a time**
5. Use clear, descriptive names for each todo item

### When to Skip Todos:
- Simple, single-line fixes
- Purely informational responses
- Reading files for understanding

## Reasoning and Careful Changes

**Always reason carefully before making changes:**

1. **Understand the context first:**
   - Read relevant files to understand the current implementation
   - Search the codebase to see how similar features are implemented
   - Check for existing patterns and conventions

2. **Plan your approach:**
   - Identify all files that need to be modified
   - Consider side effects and dependencies
   - Think about how changes align with the game specification

3. **Make incremental, testable changes:**
   - Prefer small, focused changes over large refactors
   - Ensure changes maintain existing functionality
   - Consider backward compatibility

4. **Verify your changes:**
   - Check for linter errors after making changes
   - Ensure code follows existing patterns and style
   - Consider edge cases and error handling

5. **Document your reasoning:**
   - If making non-obvious decisions, explain why in comments or commit messages
   - Reference the relevant section of `CLONE_WARS_WAR_SIM_MVP.md` when applicable

## Workflow Summary

For any coding task:

1. ✅ **Read** `CLONE_WARS_WAR_SIM_MVP.md` (or relevant sections) if working on game logic
2. ✅ **Create todos** for multi-step tasks
3. ✅ **Search and read** relevant existing code to understand patterns
4. ✅ **Reason** through the approach before making changes
5. ✅ **Implement** changes incrementally
6. ✅ **Check** for errors and verify correctness
7. ✅ **Update todos** as you complete each step

Remember: The game specification document exists to prevent design drift and ensure consistency. Always consult it first.

