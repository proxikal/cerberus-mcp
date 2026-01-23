"""
Cerberus CLI - Memory System Commands

Command-line interface for memory system operations.

Usage:
    cerberus memory propose [--interactive] [--batch] [--threshold FLOAT]
    cerberus memory install-hooks --cli CLI_NAME
    cerberus memory uninstall-hooks --cli CLI_NAME
    cerberus memory test-hooks --cli CLI_NAME
    cerberus memory session-start
    cerberus memory session-end
    cerberus memory session-status
    cerberus memory recover [SESSION_ID] [--list] [--discard]
"""

import sys
from typing import Optional


def main():
    """Main CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="cerberus",
        description="Cerberus code exploration and memory system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Memory command group
    memory_parser = subparsers.add_parser("memory", help="Memory system operations")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")

    # cerberus memory propose
    propose_parser = memory_subparsers.add_parser(
        "propose",
        help="Propose and store memories from current session"
    )
    propose_parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="Use interactive approval mode (default)"
    )
    propose_parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch mode (auto-approve high confidence)"
    )
    propose_parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Auto-approval threshold for batch mode (default: 0.9)"
    )

    # cerberus memory install-hooks
    install_parser = memory_subparsers.add_parser(
        "install-hooks",
        help="Install session hooks for CLI tool"
    )
    install_parser.add_argument(
        "--cli",
        required=True,
        choices=["claude-code", "codex-cli", "gemini-cli"],
        help="CLI tool to install hooks for"
    )

    # cerberus memory uninstall-hooks
    uninstall_parser = memory_subparsers.add_parser(
        "uninstall-hooks",
        help="Uninstall session hooks for CLI tool"
    )
    uninstall_parser.add_argument(
        "--cli",
        required=True,
        choices=["claude-code", "codex-cli", "gemini-cli"],
        help="CLI tool to uninstall hooks from"
    )

    # cerberus memory test-hooks
    test_parser = memory_subparsers.add_parser(
        "test-hooks",
        help="Test hook installation for CLI tool"
    )
    test_parser.add_argument(
        "--cli",
        required=True,
        choices=["claude-code", "codex-cli", "gemini-cli"],
        help="CLI tool to test hooks for"
    )

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate handler
    if args.command == "memory":
        handle_memory_command(args)
    else:
        parser.print_help()
        sys.exit(1)


def handle_memory_command(args):
    """Handle memory subcommands."""
    from cerberus.memory.hooks import (
        propose_hook_with_error_handling,
        install_hooks,
        uninstall_hooks,
        test_hooks
    )
    from cerberus.memory.session_lifecycle import (
        start_session,
        end_session,
        get_session_state_info,
        list_crashed_sessions,
        recover_crashed_session
    )
    from cerberus.memory.hooks import detect_context as hooks_detect_context

    if args.memory_command == "propose":
        # Propose and store memories
        interactive = args.interactive and not args.batch
        propose_hook_with_error_handling(
            interactive=interactive,
            batch_threshold=args.threshold
        )

    elif args.memory_command == "install-hooks":
        # Install session hooks
        success = install_hooks(args.cli, verbose=True)
        sys.exit(0 if success else 1)

    elif args.memory_command == "uninstall-hooks":
        # Uninstall session hooks
        success = uninstall_hooks(args.cli, verbose=True)
        sys.exit(0 if success else 1)

    elif args.memory_command == "test-hooks":
        # Test hook installation
        success = test_hooks(args.cli)
        sys.exit(0 if success else 1)

    elif args.memory_command == "session-start":
        # Manually start session
        context = hooks_detect_context()
        state = start_session(
            working_directory=context.working_directory,
            project_name=context.project_name,
            language=context.language
        )
        print(f"✓ Started session: {state.session_id}")
        print(f"  Project: {state.project_name}")
        print(f"  Language: {state.language}")

    elif args.memory_command == "session-end":
        # Manually end session
        state = end_session("explicit")
        if state:
            print(f"✓ Ended session: {state.session_id}")
            print(f"  Duration: {(state.last_activity - state.started_at).total_seconds() / 60:.1f} minutes")
            print(f"  Turns: {state.turn_count}")
            print(f"  Corrections: {len(state.corrections)}")
        else:
            print("✗ No active session found")

    elif args.memory_command == "session-status":
        # Show session status
        info = get_session_state_info()
        if info:
            print(f"Session Status:")
            print(f"  ID: {info['session_id']}")
            print(f"  Started: {info['started_at']}")
            print(f"  Duration: {info['duration_minutes']} minutes")
            print(f"  Idle: {info['idle_minutes']} minutes")
            print(f"  Project: {info['project_name']}")
            print(f"  Language: {info['language']}")
            print(f"  Turns: {info['turn_count']}")
            print(f"  Corrections: {info['correction_count']}")
            print(f"  Tools used: {info['tools_used_count']}")
            print(f"  Modified files: {info['modified_files_count']}")
        else:
            print("No active session")

    elif args.memory_command == "recover":
        # Recover crashed session
        if args.list or not args.session_id:
            # List crashed sessions
            sessions = list_crashed_sessions()
            if sessions:
                print(f"Crashed sessions available for recovery:")
                for session in sessions:
                    print(f"  {session['session_id']}")
                    print(f"    Crashed: {session['crashed_at']}")
                    print(f"    Corrections: {session['correction_count']}")
            else:
                print("No crashed sessions found")
        else:
            # Recover specific session
            success = recover_crashed_session(
                args.session_id,
                discard=args.discard
            )
            sys.exit(0 if success else 1)

    else:
        print(f"Unknown memory command: {args.memory_command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
