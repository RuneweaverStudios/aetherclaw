#!/usr/bin/env python3
"""
Aether-Claw Main CLI Entry Point

Unified command-line interface for Aether-Claw operations.
"""

import argparse
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_index(args):
    """Run brain indexer."""
    from brain_index import BrainIndexer

    indexer = BrainIndexer()

    if args.file:
        version = indexer.index_file(Path(args.file))
        print(f"Indexed {args.file} (version {version})")
    else:
        results = indexer.index_all()
        print(f"Indexed {len(results)} files:")
        for name, version in results.items():
            print(f"  {name}: v{version}")


def cmd_keygen(args):
    """Generate RSA key pair."""
    from keygen import KeyManager

    manager = KeyManager()

    if args.info:
        info = manager.get_key_info()
        print("Key Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        return

    passphrase = None
    if args.passphrase:
        import getpass
        passphrase = getpass.getpass('Enter passphrase: ').encode()

    try:
        private, public = manager.generate_key_pair(
            passphrase=passphrase,
            overwrite=args.overwrite
        )
        print(f"Key pair generated:")
        print(f"  Private: {private}")
        print(f"  Public: {public}")
    except FileExistsError as e:
        print(f"Error: {e}")
        print("Use --overwrite to replace existing keys")


def cmd_sign_skill(args):
    """Sign a skill."""
    from safe_skill_creator import SafeSkillCreator

    creator = SafeSkillCreator()

    if args.verify:
        is_valid, message = creator.verify_skill(args.verify)
        print(message)
        sys.exit(0 if is_valid else 1)

    if args.list:
        skills = creator.list_skills()
        print(f"Found {len(skills)} skills:")
        for skill in skills:
            status = "VALID" if skill.get('signature_valid') else "INVALID"
            print(f"  [{status}] {skill['name']}")
        return

    if args.create:
        try:
            signed = creator.create_skill_from_file(
                Path(args.create),
                name=args.name,
                description=args.description or "",
                skip_scan=args.skip_scan
            )
            path = creator.save_skill(signed)
            print(f"Skill signed: {path}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def cmd_verify_skills(args):
    """Verify all skills."""
    from tasks.skill_checker import check_all_skills

    result = check_all_skills()

    print(f"Total skills: {result.total_skills}")
    print(f"Valid: {result.valid_skills}")
    print(f"Invalid: {result.invalid_skills}")
    print(f"Unsigned: {result.unsigned_skills}")

    if result.invalid_skills > 0:
        print("\nInvalid skills:")
        for skill in result.skills:
            if not skill.signature_valid and skill.is_signed:
                print(f"  - {skill.skill_name}: {skill.error}")

    sys.exit(0 if result.invalid_skills == 0 else 1)


def cmd_heartbeat(args):
    """Run heartbeat daemon."""
    from heartbeat_daemon import HeartbeatDaemon

    daemon = HeartbeatDaemon(interval_minutes=args.interval)

    if args.status:
        status = daemon.get_status()
        print("Heartbeat Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        return

    if args.task:
        result = daemon.execute_task(args.task)
        print(f"Task: {result.task_name}")
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        return

    if args.run_once:
        results = daemon.run_once()
        print(f"Executed {len(results)} tasks:")
        for result in results:
            status = "OK" if result.success else "FAILED"
            print(f"  [{status}] {result.task_name}: {result.message}")
        return

    # Start daemon
    import signal

    def handle_signal(signum, frame):
        print("\nStopping...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    daemon.start()
    print(f"Heartbeat started (interval: {daemon.interval_minutes} min)")
    print("Press Ctrl+C to stop")

    import time
    while daemon._running:
        time.sleep(1)


def cmd_dashboard(args):
    """Launch Streamlit dashboard."""
    import subprocess

    port = args.port or 8501

    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        str(Path(__file__).parent / 'dashboard.py'),
        '--server.port', str(port),
        '--server.headless', 'true'
    ]

    print(f"Starting dashboard on http://localhost:{port}")
    subprocess.run(cmd)


def cmd_status(args):
    """Show system status."""
    from config_loader import load_config
    from brain_index import BrainIndexer
    from safe_skill_creator import SafeSkillCreator

    config = load_config()

    print("=" * 50)
    print("Aether-Claw Status")
    print("=" * 50)

    print(f"\nVersion: {config.version}")
    print(f"Brain Directory: {config.brain_dir}")
    print(f"Skills Directory: {config.skills_dir}")

    print("\n--- Safety ---")
    print(f"Safety Gate: {'Enabled' if config.safety_gate.enabled else 'Disabled'}")
    print(f"Kill Switch: {'Enabled' if config.kill_switch.enabled else 'Disabled'}")

    print("\n--- Memory ---")
    try:
        indexer = BrainIndexer()
        stats = indexer.get_stats()
        print(f"Indexed Files: {stats['total_files']}")
        print(f"Total Versions: {stats['total_versions']}")
        print(f"Last Indexed: {stats['last_indexed'] or 'Never'}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Skills ---")
    try:
        creator = SafeSkillCreator()
        skills = creator.list_skills()
        valid = sum(1 for s in skills if s.get('signature_valid'))
        print(f"Total Skills: {len(skills)}")
        print(f"Valid Signatures: {valid}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Swarm ---")
    print(f"Max Workers: {config.swarm.max_workers}")
    print(f"Isolation Mode: {config.swarm.isolation_mode}")

    print("\n--- Heartbeat ---")
    print(f"Enabled: {config.heartbeat.enabled}")
    print(f"Interval: {config.heartbeat.interval_minutes} min")


def cmd_kill_switch(args):
    """Manage kill switch."""
    from kill_switch import KillSwitch

    ks = KillSwitch()

    if args.arm:
        ks.arm()
        print("Kill switch ARMED")

    elif args.disarm:
        ks.disarm()
        print("Kill switch DISARMED")

    elif args.trigger:
        from kill_switch import TriggerReason
        try:
            reason = TriggerReason(args.trigger)
            ks.trigger(reason, args.details or "")
            print(f"Kill switch TRIGGERED: {reason.value}")
        except ValueError:
            print(f"Invalid reason. Valid options: {[r.value for r in TriggerReason]}")

    elif args.reset:
        if ks.reset():
            print("Kill switch RESET")
        else:
            print("Kill switch was not triggered")

    else:
        # Show status
        print(f"Armed: {ks.is_armed()}")
        print(f"Triggered: {ks.is_triggered()}")
        if ks.is_triggered():
            print(f"Reason: {ks.get_trigger_reason()}")
            print(f"Time: {ks.get_trigger_time()}")


def cmd_swarm(args):
    """Manage swarm operations."""
    from swarm.orchestrator import SwarmOrchestrator
    from swarm.worker import Task

    orchestrator = SwarmOrchestrator()

    if args.status:
        status = orchestrator.monitor_progress()
        print("Swarm Status:")
        print(f"  Total Workers: {status.total_workers}")
        print(f"  Active Workers: {status.active_workers}")
        print(f"  Pending Tasks: {status.pending_tasks}")
        print(f"  Completed Tasks: {status.completed_tasks}")
        print(f"  Failed Tasks: {status.failed_tasks}")
        return

    if args.task:
        task = Task(
            id=f"task-{args.task[:20]}",
            description=args.task
        )
        orchestrator.add_task(task)

        print(f"Running task: {args.task[:50]}...")
        results = orchestrator.run_until_complete()

        for completed in results:
            print(f"\nTask {completed.id}:")
            if completed.result:
                result_type = completed.result.get('type', 'unknown')
                print(f"  Type: {result_type}")
                if result_type == 'code':
                    code = completed.result.get('code', '')
                    print(f"  Code:\n{code[:500]}...")
                elif result_type == 'decomposition':
                    subtasks = completed.result.get('subtasks', [])
                    print(f"  Subtasks: {len(subtasks)}")
                    for st in subtasks:
                        print(f"    - {st.get('id')}: {st.get('description', '')[:50]}")
                else:
                    print(f"  Result: {str(completed.result)[:200]}")

            if completed.error:
                print(f"  Error: {completed.error}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Aether-Claw - Secure Swarm-Based AI Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # index command
    p_index = subparsers.add_parser('index', help='Index brain files')
    p_index.add_argument('--file', '-f', help='Index a specific file')
    p_index.set_defaults(func=cmd_index)

    # keygen command
    p_keygen = subparsers.add_parser('keygen', help='Generate RSA keys')
    p_keygen.add_argument('--info', '-i', action='store_true', help='Show key info')
    p_keygen.add_argument('--overwrite', '-o', action='store_true', help='Overwrite existing')
    p_keygen.add_argument('--passphrase', '-p', action='store_true', help='Use passphrase')
    p_keygen.set_defaults(func=cmd_keygen)

    # sign-skill command
    p_sign = subparsers.add_parser('sign-skill', help='Sign a skill')
    p_sign.add_argument('--create', '-c', help='Create skill from file')
    p_sign.add_argument('--name', '-n', help='Skill name')
    p_sign.add_argument('--description', '-d', help='Skill description')
    p_sign.add_argument('--verify', '-v', help='Verify a skill')
    p_sign.add_argument('--list', '-l', action='store_true', help='List skills')
    p_sign.add_argument('--skip-scan', action='store_true', help='Skip security scan')
    p_sign.set_defaults(func=cmd_sign_skill)

    # verify-skills command
    p_verify = subparsers.add_parser('verify-skills', help='Verify all skills')
    p_verify.set_defaults(func=cmd_verify_skills)

    # heartbeat command
    p_heartbeat = subparsers.add_parser('heartbeat', help='Run heartbeat daemon')
    p_heartbeat.add_argument('--status', action='store_true', help='Show status')
    p_heartbeat.add_argument('--run-once', action='store_true', help='Run once')
    p_heartbeat.add_argument('--task', '-t', help='Execute specific task')
    p_heartbeat.add_argument('--interval', '-i', type=int, default=30, help='Interval in minutes')
    p_heartbeat.set_defaults(func=cmd_heartbeat)

    # dashboard command
    p_dashboard = subparsers.add_parser('dashboard', help='Launch dashboard')
    p_dashboard.add_argument('--port', '-p', type=int, help='Port number')
    p_dashboard.set_defaults(func=cmd_dashboard)

    # status command
    p_status = subparsers.add_parser('status', help='Show system status')
    p_status.set_defaults(func=cmd_status)

    # kill-switch command
    p_kill = subparsers.add_parser('kill-switch', help='Manage kill switch')
    p_kill.add_argument('--arm', action='store_true', help='Arm kill switch')
    p_kill.add_argument('--disarm', action='store_true', help='Disarm kill switch')
    p_kill.add_argument('--trigger', '-t', help='Trigger with reason')
    p_kill.add_argument('--details', '-d', help='Trigger details')
    p_kill.add_argument('--reset', action='store_true', help='Reset kill switch')
    p_kill.set_defaults(func=cmd_kill_switch)

    # swarm command
    p_swarm = subparsers.add_parser('swarm', help='Manage swarm')
    p_swarm.add_argument('--status', action='store_true', help='Show swarm status')
    p_swarm.add_argument('--task', '-t', help='Execute a task')
    p_swarm.set_defaults(func=cmd_swarm)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
