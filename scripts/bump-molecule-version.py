#!/usr/bin/env python3
"""
Bump molecule versions based on conventional commits.

This script:
1. Finds all commits since last release that affect each molecule
2. Determines version bump type (major/minor/patch) from commit messages
3. Updates __version__ in molecule __init__.py files

Usage:
    python scripts/bump-molecule-version.py [--dry-run] [--molecule <name>]

Examples:
    # Bump all molecules based on commits
    python scripts/bump-molecule-version.py

    # Dry run (show what would change)
    python scripts/bump-molecule-version.py --dry-run

    # Bump specific molecule
    python scripts/bump-molecule-version.py --molecule fossa
"""
import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from packaging import version

MOLECULES_DIR = Path(__file__).parent.parent / "devgraph_integrations" / "molecules"


def parse_commit_message(message: str) -> Optional[Tuple[str, str, str, bool]]:
    """
    Parse conventional commit message.

    Returns:
        Tuple of (type, scope, subject, breaking) or None if not conventional
    """
    # Pattern: type(scope): subject
    pattern = r"^(\w+)(?:\(([^)]+)\))?: (.+?)(?:\n\n.*BREAKING CHANGE)?$"
    match = re.match(pattern, message, re.DOTALL)

    if not match:
        return None

    commit_type, scope, subject = match.groups()
    breaking = "BREAKING CHANGE" in message or subject.endswith("!")

    return commit_type, scope or "", subject, breaking


def get_commits_since_tag(tag: Optional[str] = None) -> List[str]:
    """Get commit messages since tag (or all if no tag)."""
    try:
        if tag:
            cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"]
        else:
            # Get all commits
            cmd = ["git", "log", "--pretty=format:%s"]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    except subprocess.CalledProcessError:
        return []


def determine_bump_type(commits: List[str]) -> str:
    """
    Determine version bump type from commits.

    Returns:
        'major', 'minor', 'patch', or 'none'
    """
    has_breaking = False
    has_feat = False
    has_fix = False

    for commit_msg in commits:
        parsed = parse_commit_message(commit_msg)
        if not parsed:
            continue

        commit_type, _, _, breaking = parsed

        if breaking:
            has_breaking = True
        elif commit_type == "feat":
            has_feat = True
        elif commit_type == "fix":
            has_fix = True

    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    elif has_fix:
        return "patch"
    else:
        return "none"


def get_molecule_commits(molecule_name: str, commits: List[str]) -> List[str]:
    """Filter commits that affect a specific molecule."""
    molecule_commits = []

    for commit_msg in commits:
        parsed = parse_commit_message(commit_msg)
        if not parsed:
            continue

        _, scope, _, _ = parsed

        # Check if scope matches molecule
        if scope == molecule_name:
            molecule_commits.append(commit_msg)

    return molecule_commits


def bump_version(current: str, bump_type: str) -> str:
    """Bump semantic version."""
    v = version.parse(current)
    major, minor, patch = v.major, v.minor, v.micro

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        return current


def get_current_version(init_file: Path) -> Optional[str]:
    """Extract current version from __init__.py."""
    if not init_file.exists():
        return None

    content = init_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def update_version_in_file(init_file: Path, new_version: str) -> None:
    """Update __version__ in __init__.py."""
    content = init_file.read_text()
    updated = re.sub(
        r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{new_version}\g<2>",
        content,
    )

    # Also update in metadata dict
    updated = re.sub(
        r'("version":\s*__version__|"version":\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{new_version}\g<2>",
        updated,
    )

    init_file.write_text(updated)


def main():
    parser = argparse.ArgumentParser(description="Bump molecule versions")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying"
    )
    parser.add_argument("--molecule", help="Bump specific molecule only")
    parser.add_argument("--since-tag", help="Check commits since this git tag")
    args = parser.parse_args()

    # Get all commits
    commits = get_commits_since_tag(args.since_tag)

    if not commits:
        print("No commits found")
        return

    # Discover molecules
    molecules = [
        d for d in MOLECULES_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")
    ]

    if args.molecule:
        molecules = [m for m in molecules if m.name == args.molecule]
        if not molecules:
            print(f"Molecule '{args.molecule}' not found")
            return

    print(f"Checking {len(commits)} commits for version bumps...\n")

    changes = []

    for molecule_dir in sorted(molecules):
        molecule_name = molecule_dir.name
        init_file = molecule_dir / "__init__.py"

        if not init_file.exists():
            continue

        # Get current version
        current_version = get_current_version(init_file)
        if not current_version:
            print(f"⚠️  {molecule_name}: No version found, skipping")
            continue

        # Get commits affecting this molecule
        molecule_commits = get_molecule_commits(molecule_name, commits)

        if not molecule_commits:
            print(f"ℹ️  {molecule_name}: No commits, staying at v{current_version}")
            continue

        # Determine bump type
        bump_type = determine_bump_type(molecule_commits)

        if bump_type == "none":
            print(
                f"ℹ️  {molecule_name}: No version-bumping commits, staying at v{current_version}"
            )
            continue

        # Calculate new version
        new_version = bump_version(current_version, bump_type)

        print(f"📦 {molecule_name}: v{current_version} → v{new_version} ({bump_type})")
        print(f"   Based on {len(molecule_commits)} commit(s):")
        for commit in molecule_commits[:3]:
            print(f"     - {commit[:80]}")
        if len(molecule_commits) > 3:
            print(f"     ... and {len(molecule_commits) - 3} more")
        print()

        changes.append((molecule_name, init_file, new_version))

    # Apply changes
    if changes and not args.dry_run:
        print("\nApplying changes...")
        for molecule_name, init_file, new_version in changes:
            update_version_in_file(init_file, new_version)
            print(f"✓ Updated {molecule_name}")

        print(f"\n✨ Updated {len(changes)} molecule(s)")
    elif changes and args.dry_run:
        print("\n(Dry run - no changes applied)")
    else:
        print("\nNo version bumps needed")


if __name__ == "__main__":
    main()
