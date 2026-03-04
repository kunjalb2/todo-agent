"""Code review tools for the AI agent."""
import os
import subprocess
from pathlib import Path
from typing import Optional

from agents.tool import function_tool


# Security constants
MAX_FILE_SIZE = 1_000_000  # 1MB
MAX_SNIPPET_SIZE = 50_000  # 50KB
MAX_DIFF_SIZE = 100_000  # 100KB

# Project root - defaults to current directory, can be overridden
PROJECT_ROOT = Path(os.getcwd()).resolve()


def validate_file_path(file_path: str, user_id: int) -> tuple[bool, str, Optional[Path]]:
    """Validate that a file path is safe to access.

    Args:
        file_path: The file path to validate
        user_id: The ID of the current user (for logging)

    Returns:
        Tuple of (is_valid, error_message, resolved_path)
    """
    try:
        # Resolve the path to its absolute form
        resolved = Path(file_path).resolve()

        # Check if path is within project root
        try:
            resolved.relative_to(PROJECT_ROOT)
        except ValueError:
            return False, "File path must be within the project directory", None

        # Check for suspicious patterns
        if ".." in str(resolved):
            return False, "File path cannot contain parent directory references", None

        # Check if file exists and is a file (not directory)
        if not resolved.exists():
            return False, f"File not found: {file_path}", None

        if not resolved.is_file():
            return False, "Path must be a file, not a directory", None

        # Check file size
        file_size = resolved.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large ({file_size} bytes, max {MAX_FILE_SIZE})", None

        # Check if file is readable (text-based)
        # Skip binary files by checking extension
        binary_extensions = {
            ".pyc", ".so", ".dll", ".exe", ".bin", ".tar", ".gz", ".zip",
            ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp3", ".mp4", ".ico",
        }
        if resolved.suffix.lower() in binary_extensions:
            return False, "Cannot review binary files", None

        return True, "", resolved

    except Exception as e:
        return False, f"Error validating file path: {str(e)}", None


@function_tool
async def review_code_snippet(
    user_id: int,
    code: str,
    language: str = "python",
    focus_areas: str = "security,bugs,style,best_practices",
) -> str:
    """Review a pasted code snippet for issues.

    Args:
        user_id: The ID of the current user
        code: The code snippet to review
        language: Programming language (python, javascript, typescript, java, etc.)
        focus_areas: Comma-separated list of areas to focus on:
                    security, bugs, style, architecture, performance, best_practices

    Returns:
        Structured feedback on issues found in the code
    """
    # Check snippet size
    code_size = len(code.encode("utf-8"))
    if code_size > MAX_SNIPPET_SIZE:
        return f"Code snippet too large ({code_size} bytes, max {MAX_SNIPPET_SIZE}). Please provide a smaller snippet."

    if not code.strip():
        return "No code provided to review."

    # Parse focus areas
    areas = [area.strip() for area in focus_areas.lower().split(",") if area.strip()]
    valid_areas = {"security", "bugs", "style", "architecture", "performance", "best_practices"}
    filtered_areas = [a for a in areas if a in valid_areas]

    focus_display = ", ".join(filtered_areas) if filtered_areas else "general code quality"

    return (
        f"Reviewing {language} code snippet (focus: {focus_display})...\n\n"
        f"Please analyze the following {language} code:\n\n"
        f"```{language}\n{code}\n```\n\n"
        f"Provide a comprehensive review focusing on: {focus_display}.\n"
        f"Include:\n"
        f"- Severity levels (Critical, High, Medium, Low, Info)\n"
        f"- Specific line references when applicable\n"
        f"- Actionable suggestions for fixes\n"
        f"- Code examples for improvements\n"
    )


@function_tool
async def review_file(
    user_id: int,
    file_path: str,
    focus_areas: str = "security,bugs,style,best_practices",
) -> str:
    """Read and review a file from the codebase.

    Args:
        user_id: The ID of the current user
        file_path: Path to the file to review (relative to project root)
        focus_areas: Comma-separated list of areas to focus on:
                    security, bugs, style, architecture, performance, best_practices

    Returns:
        Review results for the specified file
    """
    # Validate file path
    is_valid, error_msg, resolved_path = validate_file_path(file_path, user_id)

    if not is_valid:
        return f"Cannot review file: {error_msg}"

    try:
        # Detect language from file extension
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".sql": "sql",
            ".sh": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".md": "markdown",
        }
        language = ext_to_lang.get(resolved_path.suffix.lower(), "text")

        # Read file content
        with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Parse focus areas
        areas = [area.strip() for area in focus_areas.lower().split(",") if area.strip()]
        valid_areas = {"security", "bugs", "style", "architecture", "performance", "best_practices"}
        filtered_areas = [a for a in areas if a in valid_areas]

        focus_display = ", ".join(filtered_areas) if filtered_areas else "general code quality"

        # Get relative path for display
        try:
            relative_path = resolved_path.relative_to(PROJECT_ROOT)
        except ValueError:
            relative_path = resolved_path

        return (
            f"Reviewing file: `{relative_path}` ({language}, focus: {focus_display})\n\n"
            f"Please analyze the following {language} code:\n\n"
            f"```{language}\n{content}\n```\n\n"
            f"Provide a comprehensive review focusing on: {focus_display}.\n"
            f"Include:\n"
            f"- Severity levels (Critical, High, Medium, Low, Info)\n"
            f"- Specific line references when applicable\n"
            f"- Actionable suggestions for fixes\n"
            f"- Code examples for improvements\n"
        )

    except UnicodeDecodeError:
        return "Cannot read file: contains binary or non-text content."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@function_tool
async def review_git_diff(
    user_id: int,
    staged_only: bool = False,
    focus_areas: str = "security,bugs,style,best_practices",
) -> str:
    """Review git diff changes.

    Args:
        user_id: The ID of the current user
        staged_only: If True, review staged changes (git diff --staged).
                    If False, review unstaged changes (git diff).
        focus_areas: Comma-separated list of areas to focus on:
                    security, bugs, style, architecture, performance, best_practices

    Returns:
        Review results for the git diff
    """
    try:
        # Check if we're in a git repository
        git_dir = Path(PROJECT_ROOT) / ".git"
        if not git_dir.exists():
            return "Not in a git repository. Cannot review git diff."

        # Build git command
        cmd = ["git", "diff"]
        if staged_only:
            cmd.append("--staged")

        # Run git diff
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return f"Error running git diff: {result.stderr}"

        diff_content = result.stdout

        # Check diff size
        diff_size = len(diff_content.encode("utf-8"))
        if diff_size > MAX_DIFF_SIZE:
            return f"Diff too large ({diff_size} bytes, max {MAX_DIFF_SIZE}). Please review smaller changes."

        if not diff_content.strip():
            if staged_only:
                return "No staged changes to review."
            return "No unstaged changes to review."

        # Parse focus areas
        areas = [area.strip() for area in focus_areas.lower().split(",") if area.strip()]
        valid_areas = {"security", "bugs", "style", "architecture", "performance", "best_practices"}
        filtered_areas = [a for a in areas if a in valid_areas]

        focus_display = ", ".join(filtered_areas) if filtered_areas else "general code quality"

        diff_type = "staged" if staged_only else "unstaged"

        return (
            f"Reviewing {diff_type} changes (focus: {focus_display})...\n\n"
            f"Please analyze the following git diff:\n\n"
            f"```diff\n{diff_content}\n```\n\n"
            f"Provide a comprehensive review focusing on: {focus_display}.\n"
            f"Include:\n"
            f"- Severity levels (Critical, High, Medium, Low, Info)\n"
            f"- Comments on specific changed lines\n"
            f"- Actionable suggestions for improvements\n"
            f"- Potential bugs or issues introduced\n"
        )

    except subprocess.TimeoutExpired:
        return "Error: git diff command timed out."
    except FileNotFoundError:
        return "Error: git command not found. Please ensure git is installed."
    except Exception as e:
        return f"Error reviewing git diff: {str(e)}"


@function_tool
async def list_reviewable_files(
    user_id: int,
    directory: str = ".",
    max_depth: int = 3,
) -> str:
    """List files that can be reviewed in the project.

    Args:
        user_id: The ID of the current user
        directory: Directory to list (relative to project root)
        max_depth: Maximum directory depth to traverse

    Returns:
        String representation of reviewable files
    """
    try:
        # Resolve directory path
        dir_path = Path(directory)
        if not dir_path.is_absolute():
            dir_path = PROJECT_ROOT / dir_path

        # Validate path
        try:
            dir_path.relative_to(PROJECT_ROOT)
        except ValueError:
            return f"Directory must be within project root: {directory}"

        if not dir_path.exists():
            return f"Directory not found: {directory}"

        if not dir_path.is_dir():
            return f"Path is not a directory: {directory}"

        # Binary extensions to skip
        binary_extensions = {
            ".pyc", ".so", ".dll", ".exe", ".bin", ".tar", ".gz", ".zip",
            ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp3", ".mp4", ".ico",
            ".woff", ".woff2", ".ttf", ".eot",
        }

        # Directories to skip
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                     "dist", "build", ".next", "target", "bin", "obj"}

        # Collect files
        files_info = []
        file_count = 0
        max_files = 500

        for root in sorted(dir_path.rglob("*")):
            # Check depth
            try:
                rel_path = root.relative_to(dir_path)
                depth = len(rel_path.parts)
            except ValueError:
                continue

            if depth > max_depth:
                continue

            # Skip directories in skip list
            if any(part in skip_dirs for part in root.parts):
                continue

            if root.is_file():
                # Skip binary files
                if root.suffix.lower() in binary_extensions:
                    continue

                # Skip files that are too large
                try:
                    if root.stat().st_size > MAX_FILE_SIZE:
                        continue
                except OSError:
                    continue

                try:
                    relative = root.relative_to(PROJECT_ROOT)
                    files_info.append(str(relative))
                    file_count += 1

                    if file_count >= max_files:
                        files_info.append(f"\n... (showing first {max_files} files)")
                        break
                except ValueError:
                    continue

        if not files_info:
            return f"No reviewable files found in: {directory}"

        return (
            f"Reviewable files in `{directory}` "
            f"(showing first {min(file_count, max_files)} files):\n\n"
            + "\n".join(files_info)
        )

    except Exception as e:
        return f"Error listing files: {str(e)}"
