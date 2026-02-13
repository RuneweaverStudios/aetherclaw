#!/usr/bin/env python3
"""
Aether-Claw Dashboard

Streamlit-based dashboard for monitoring and controlling Aether-Claw.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Page config
st.set_page_config(
    page_title="Aether-Claw Dashboard",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_config():
    """Load configuration."""
    try:
        from config_loader import load_config
        return load_config()
    except Exception:
        return None


def get_audit_log():
    """Get audit log entries."""
    audit_file = Path(__file__).parent / 'brain' / 'audit_log.md'

    if not audit_file.exists():
        return []

    entries = []
    current_entry = []

    with open(audit_file, 'r') as f:
        for line in f:
            if line.startswith('### '):
                if current_entry:
                    entries.append(''.join(current_entry))
                current_entry = [line]
            elif current_entry:
                current_entry.append(line)

    return entries[-50:]  # Last 50 entries


def get_skills_status():
    """Get skills status."""
    try:
        from safe_skill_creator import SafeSkillCreator
        creator = SafeSkillCreator()
        return creator.list_skills()
    except Exception as e:
        return []


def get_brain_files():
    """Get brain files."""
    brain_dir = Path(__file__).parent / 'brain'

    if not brain_dir.exists():
        return []

    files = []
    for f in brain_dir.glob('*.md'):
        with open(f, 'r') as file:
            content = file.read()
        files.append({
            'name': f.name,
            'path': str(f),
            'content': content,
            'size': len(content)
        })

    return files


def get_heartbeat_status():
    """Get heartbeat status."""
    try:
        from heartbeat_daemon import HeartbeatDaemon
        daemon = HeartbeatDaemon()
        return daemon.get_status()
    except Exception:
        return {'running': False}


def main():
    """Main dashboard application."""

    # Sidebar
    st.sidebar.title("🦁 Aether-Claw")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Live Logs", "Brain Editor", "Heartbeat", "Skills", "Swarm"]
    )

    # Load config
    config = load_config()

    # Header
    st.title(f"Aether-Claw Dashboard")
    st.markdown(f"*Secure Swarm-Based AI Assistant*")

    if config:
        st.caption(f"Version {config.version} | Brain: {config.brain_dir}")

    st.markdown("---")

    # Pages
    if page == "Overview":
        render_overview(config)
    elif page == "Live Logs":
        render_live_logs()
    elif page == "Brain Editor":
        render_brain_editor()
    elif page == "Heartbeat":
        render_heartbeat()
    elif page == "Skills":
        render_skills()
    elif page == "Swarm":
        render_swarm()


def render_overview(config):
    """Render overview page."""
    st.header("System Overview")

    col1, col2, col3 = st.columns(3)

    # System status
    with col1:
        st.subheader("System Status")
        st.metric("Safety Gate", "Enabled" if config and config.safety_gate.enabled else "Disabled")
        st.metric("Kill Switch", "Armed" if config and config.kill_switch.enabled else "Disarmed")
        st.metric("Heartbeat", "Running" if get_heartbeat_status().get('running') else "Stopped")

    # Memory status
    with col2:
        st.subheader("Memory")
        brain_files = get_brain_files()
        st.metric("Brain Files", len(brain_files))

        try:
            from brain_index import BrainIndexer
            indexer = BrainIndexer()
            stats = indexer.get_stats()
            st.metric("Indexed Files", stats.get('total_files', 0))
            st.metric("Total Versions", stats.get('total_versions', 0))
        except Exception:
            st.metric("Index", "Not available")

    # Skills status
    with col3:
        st.subheader("Skills")
        skills = get_skills_status()
        valid = sum(1 for s in skills if s.get('signature_valid'))
        st.metric("Total Skills", len(skills))
        st.metric("Valid Signatures", valid)

        if len(skills) > valid:
            st.warning(f"⚠️ {len(skills) - valid} skills have invalid signatures!")

    # Recent activity
    st.subheader("Recent Activity")
    logs = get_audit_log()[:10]

    if logs:
        for log in logs:
            with st.expander(log.split('\n')[0][:80], expanded=False):
                st.code(log, language='markdown')
    else:
        st.info("No recent activity")


def render_live_logs():
    """Render live logs page."""
    st.header("Live Logs")

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        if st.button("Refresh") or auto_refresh:
            st.rerun()

    # Log level filter
    level_filter = st.multiselect(
        "Filter by level",
        ["INFO", "WARN", "ERROR", "SECURITY", "AUDIT"],
        default=["INFO", "WARN", "ERROR", "SECURITY"]
    )

    # Get logs
    logs = get_audit_log()

    # Filter
    filtered = []
    for log in logs:
        for level in level_filter:
            if f"| {level} |" in log:
                filtered.append(log)
                break

    st.write(f"Showing {len(filtered)} entries")

    # Display
    for log in filtered[-30:]:
        lines = log.strip().split('\n')
        header = lines[0] if lines else log[:100]

        # Determine color based on level
        if "| ERROR |" in header or "| SECURITY |" in header:
            st.error(header)
        elif "| WARN |" in header:
            st.warning(header)
        else:
            st.info(header)

        with st.expander("Details"):
            st.code(log, language='markdown')


def render_brain_editor():
    """Render brain editor page."""
    st.header("Brain Editor")

    brain_files = get_brain_files()

    if not brain_files:
        st.warning("No brain files found")
        return

    # File selector
    file_names = [f['name'] for f in brain_files]
    selected = st.selectbox("Select file", file_names)

    # Find selected file
    selected_file = next((f for f in brain_files if f['name'] == selected), None)

    if selected_file:
        col1, col2 = st.columns([3, 1])
        with col2:
            st.metric("Size", f"{selected_file['size']} chars")

        # Editor
        new_content = st.text_area(
            "Edit content",
            selected_file['content'],
            height=400
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes"):
                try:
                    with open(selected_file['path'], 'w') as f:
                        f.write(new_content)
                    st.success(f"Saved {selected}")

                    # Re-index
                    try:
                        from brain_index import BrainIndexer
                        indexer = BrainIndexer()
                        indexer.index_file(Path(selected_file['path']))
                        st.info("Re-indexed")
                    except Exception as e:
                        st.warning(f"Could not re-index: {e}")

                except Exception as e:
                    st.error(f"Error saving: {e}")

        with col2:
            if st.button("View History"):
                try:
                    from brain_index import BrainIndexer
                    indexer = BrainIndexer()
                    history = indexer.get_file_history(selected)

                    if history:
                        st.write(f"**{len(history)} versions**")
                        for h in history[-5:]:
                            st.write(f"- v{h['version']}: {h['timestamp']}")
                    else:
                        st.info("No history available")
                except Exception as e:
                    st.error(f"Error getting history: {e}")


def render_heartbeat():
    """Render heartbeat page."""
    st.header("Heartbeat Status")

    status = get_heartbeat_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        running = status.get('running', False)
        st.metric("Status", "Running" if running else "Stopped")

    with col2:
        st.metric("Interval", f"{status.get('interval_minutes', 30)} min")

    with col3:
        st.metric("Tasks Registered", len(status.get('registered_tasks', [])))

    # Last run
    if status.get('last_run'):
        st.info(f"Last run: {status['last_run']}")

    # Registered tasks
    st.subheader("Registered Tasks")
    tasks = status.get('registered_tasks', [])

    if tasks:
        for task in tasks:
            st.write(f"- {task}")
    else:
        st.info("No tasks registered")

    # Controls
    st.subheader("Controls")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Run Heartbeat Once"):
            try:
                from heartbeat_daemon import HeartbeatDaemon
                daemon = HeartbeatDaemon()
                results = daemon.run_once()

                st.success(f"Completed {len(results)} tasks")

                for result in results:
                    status_icon = "✅" if result.success else "❌"
                    st.write(f"{status_icon} {result.task_name}: {result.message}")

            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.button("Re-index Memory"):
            try:
                from brain_index import BrainIndexer
                indexer = BrainIndexer()
                results = indexer.index_all()

                st.success(f"Indexed {len(results)} files")
                for name, version in results.items():
                    st.write(f"- {name}: v{version}")

            except Exception as e:
                st.error(f"Error: {e}")


def render_skills():
    """Render skills page."""
    st.header("Skill Verification")

    skills = get_skills_status()

    if not skills:
        st.info("No skills found in skills/ directory")
        return

    # Summary
    valid = sum(1 for s in skills if s.get('signature_valid'))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Skills", len(skills))
    with col2:
        st.metric("Valid Signatures", valid)
    with col3:
        invalid = len(skills) - valid
        if invalid > 0:
            st.metric("Invalid/Unsigned", invalid, delta_color="inverse")
        else:
            st.metric("Invalid/Unsigned", 0)

    # Skill list
    st.subheader("Skill Registry")

    for skill in skills:
        name = skill.get('name', 'Unknown')
        is_valid = skill.get('signature_valid', False)
        scan_passed = skill.get('scan_passed', True)

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if is_valid:
                st.write(f"✅ **{name}**")
            else:
                st.write(f"❌ **{name}**")

        with col2:
            sig_status = "Valid" if is_valid else "Invalid"
            st.write(f"Signature: {sig_status}")

        with col3:
            scan_status = "Passed" if scan_passed else "Failed"
            st.write(f"Scan: {scan_status}")

        if 'error' in skill:
            st.error(f"Error: {skill['error']}")

        st.markdown("---")


def render_swarm():
    """Render swarm page."""
    st.header("Swarm Status")

    # Try to get swarm status
    try:
        from swarm.orchestrator import SwarmOrchestrator

        orchestrator = SwarmOrchestrator()
        status = orchestrator.monitor_progress()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Workers", status.total_workers)
        with col2:
            st.metric("Active", status.active_workers)
        with col3:
            st.metric("Completed", status.completed_tasks)
        with col4:
            st.metric("Failed", status.failed_tasks)

    except Exception as e:
        st.warning(f"Could not get swarm status: {e}")

    # Swarm controls
    st.subheader("Swarm Controls")

    st.info("Use the CLI (`aether_claw.py`) to manage swarm operations")

    st.code("""
# Start a task
python aether_claw.py swarm --task "Your task here"

# Check status
python aether_claw.py swarm --status
    """)


if __name__ == '__main__':
    main()
