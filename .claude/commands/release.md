---
description: Interactive Release Manager workflow. Handles version calculation, branch creation, QA gates, and changelog generation.
---

# Release Manager Workflow

You are the **Release Manager**. Your goal is to prepare a production-grade release artifact.
Follow this strict protocol. Do not skip Quality Gates.

## 1. Analysis & Version Selection
1.  **Fetch History:** Run `git fetch --tags` and `git pull origin main`.
2.  **Identify Current State:**
    - Find the latest tag: `git describe --tags --abbrev=0`.
    - Analyze commits since that tag to suggest the impact (Patch/Minor/Major).
3.  **Interactive Choice:**
    - **Ask the user** to select the target release type:
        1.  **Alpha** (e.g., `v1.1.0-alpha.1`) - Internal testing.
        2.  **Beta** (e.g., `v1.1.0-beta.1`) - Feature freeze / QA.
        3.  **Stable** (e.g., `v1.1.0`) - Production ready.
    - *Wait for user input before proceeding.*

## 2. Release Branch Setup
Once the version (let's call it `TARGET_VERSION`) is confirmed:

1.  **Create Branch:** Create a dedicated release branch from `main`:
    - Command: `git checkout -b release/TARGET_VERSION`
    - *Example:* `git checkout -b release/v1.2.0-beta.1`
2.  **Consolidate (Optional):** Ask the user: *"Are there any specific feature branches that need to be merged into this release now?"*
    - If yes: Attempt to merge them (`git merge feature/...`). Handle conflicts if any.

## 3. Quality Gate (Blocking)
**CRITICAL:** If any step fails, **ABORT** the release process immediately and report the error.

1.  **Static Analysis:**
    - `ruff check app` (if available)
    - `python -m mypy app --ignore-missing-imports` (if available)
2.  **Import Verification:**
    - `python -c "from app.main import app"` (ensure app boots without errors)
3.  **Tests:**
    - `pytest tests/` (run all tests)
4.  **Migration Check:**
    - `alembic check` or `alembic upgrade head` on a test database to verify migrations apply cleanly.

## 4. Artifact Preparation
If Quality Gate passes:

1.  **Bump Version:**
    - Update `version` in `pyproject.toml`.
2.  **Generate Changelog:**
    - Scan commits since the last tag.
    - Group them by: `Features`, `Fixes`, `Performance`, `Breaking Changes`.
    - Append this to `CHANGELOG.md` (or create a draft in the chat for the user).
3.  **Commit Release Candidate:**
    - `git add .`
    - `git commit -m "chore(release): prepare release TARGET_VERSION"`

## 5. Final Output & Instructions
1.  Push the release branch: `git push origin release/TARGET_VERSION`.
2.  Create PR, merge, and tag:
    ```bash
    gh pr create --base main --head release/TARGET_VERSION --title "Release TARGET_VERSION" --body "..."
    # After merge:
    git tag -a TARGET_VERSION -m "Release TARGET_VERSION"
    git push origin TARGET_VERSION
    ```
3.  **CRITICAL — Create GitHub Release:**
    ```bash
    gh release create TARGET_VERSION --title "TARGET_VERSION" --notes "changelog here"
    ```
    - Use `--prerelease` for alpha/beta tags.
    - Group changes by type: Features, Bug Fixes, Performance, Breaking Changes.
    - **Never skip this step.** Every tag MUST have a corresponding GitHub Release and a `release/` branch.

---
**User Request:**
