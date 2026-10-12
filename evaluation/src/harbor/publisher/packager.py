"""File collection and content hashing for task packages.

Shared logic used by both the publisher and the `harbor add` command.
"""

import hashlib
from pathlib import Path

import pathspec

from harbor.models.task.paths import TaskPaths

DEFAULT_IGNORES = [
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*~",
]


class Packager:
    """Collects task files and computes content hashes."""

    @staticmethod
    def collect_files(task_dir: Path) -> list[Path]:
        """Collect publishable files from a task directory."""
        task_dir = task_dir.resolve()
        paths = TaskPaths.from_task_dir(task_dir)

        files: list[Path] = []

        # Single files
        for single in (paths.config_path, paths.instruction_path, paths.readme_path):
            if single.exists():
                files.append(single)

        # Recursive directories. steps_dir covers per-step instruction.md,
        # tests/, solution/, workdir/, and setup.sh for multi-step tasks; it
        # simply doesn't exist for single-step tasks.
        for directory in (
            paths.environment_dir,
            paths.tests_dir,
            paths.solution_dir,
            paths.steps_dir,
        ):
            if directory.exists():
                for p in directory.rglob("*"):
                    if p.is_file():
                        files.append(p)

        # Apply gitignore / default ignore filtering
        if paths.gitignore_path.exists():
            spec = pathspec.PathSpec.from_lines(
                "gitignore", paths.gitignore_path.read_text().splitlines()
            )
        else:
            spec = pathspec.PathSpec.from_lines("gitignore", DEFAULT_IGNORES)

        files = [
            f
            for f in files
            if not spec.match_file(
                Packager.package_rel_path(task_dir, f, paths).as_posix()
            )
        ]

        files.sort(key=lambda p: Packager.package_rel_path(task_dir, p, paths).as_posix())
        return files

    @staticmethod
    def package_rel_path(
        task_dir: Path,
        file_path: Path,
        paths: TaskPaths | None = None,
    ) -> Path:
        """Return the file's path inside a task archive/package."""
        task_dir = task_dir.resolve()
        file_path = file_path.resolve()
        paths = paths or TaskPaths.from_task_dir(task_dir)

        if file_path.is_relative_to(task_dir):
            return file_path.relative_to(task_dir)

        environment_dir = paths.environment_dir.resolve()
        if file_path.is_relative_to(environment_dir):
            return Path("environment") / file_path.relative_to(environment_dir)

        raise ValueError(f"File {file_path} is outside task package roots.")

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute SHA-256 digest for a single file."""
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def compute_content_hash(task_dir: Path) -> tuple[str, list[Path]]:
        """Collect files and compute SHA-256 content hash for a task directory.

        Returns (content_hash, files).
        """
        task_dir = task_dir.resolve()
        paths = TaskPaths.from_task_dir(task_dir)
        files = Packager.collect_files(task_dir)
        outer = hashlib.sha256()
        for f in files:
            rel = Packager.package_rel_path(task_dir, f, paths).as_posix()
            file_hash = Packager.compute_file_hash(f)
            outer.update(f"{rel}\0{file_hash}\n".encode())
        return outer.hexdigest(), files
