"""
Configuration for incremental update operations.
"""

INCREMENTAL_CONFIG = {
    "enable_git_integration": True,
    "reparse_callers_on_signature_change": True,
    "max_affected_callers_to_reparse": 50,  # Limit for large call graphs
    "store_git_commit_in_index": True,
    "fallback_to_full_reparse_threshold": 0.3,  # If >30% files changed, do full reparse
}

GIT_CONFIG = {
    "respect_gitignore": True,
    "compare_against": "HEAD",  # or "last_index_commit"
    "include_untracked": True,
}
