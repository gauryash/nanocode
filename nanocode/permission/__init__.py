"""NanoCode Permission Manager — workspace jail for safe file operations.

Every filesystem operation passes through PermissionManager, which:
- Validates path containment within the workspace
- Rejects path traversal and symlink escapes
- Requires user confirmation for sensitive and out-of-workspace files
- Persists approvals per workspace
"""

from nanocode.permission.manager import PermissionManager
from nanocode.permission.path_validator import PathValidator
from nanocode.permission.permission_store import PermissionStore
from nanocode.permission.permission_prompt import PermissionPrompt
from nanocode.permission.fs_wrapper import FileSystemWrapper

__all__ = [
    "PermissionManager",
    "PathValidator",
    "PermissionStore",
    "PermissionPrompt",
    "FileSystemWrapper",
]
