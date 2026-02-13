#!/usr/bin/env python3
"""
Aether-Claw Dashboard

Streamlit-based web interface with chat, monitoring, and Telegram integration.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Page config
st.set_page_config(
    page_title="Aether-Claw",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage { padding: 10px; border-radius: 8px; margin: 5px 0; }
    .block-container { padding-top: 2rem; }
    .stMetric > div { background-color: #1a1a2e; border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


def get_api_client():
    """Get GLM client."""
    from glm_client import GLMClient, ModelTier
    return GLMClient(), ModelTier


def get_system_status() -> dict:
    """Get system status."""
    try:
        from config_loader import load_config
        from brain_index import BrainIndexer
        from safe_skill_creator import SafeSkillCreator
        from kill_switch import get_kill_switch

        config = load_config()
        indexer = BrainIndexer()
        stats = indexer.get_stats()
        creator = SafeSkillCreator()
        skills = creator.list_skills()
        ks = get_kill_switch()

        return {
            "version": config.version,
            "indexed_files": stats['total_files'],
            "total_versions": stats['total_versions'],
            "skills": len(skills),
            "valid_skills": sum(1 for s in skills if s.get('signature_valid')),
            "heartbeat_enabled": config.heartbeat.enabled,
            "heartbeat_interval": config.heartbeat.interval_minutes,
            "safety_gate": config.safety_gate.enabled,
            "kill_switch_armed": ks.is_armed(),
            "kill_switch_triggered": ks.is_triggered(),
        }
    except Exception as e:
        return {"error": str(e)}


def init_session_state():
    """Initialize session state."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "telegram_enabled" not in st.session_state:
        st.session_state.telegram_enabled = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    if "telegram_token" not in st.session_state:
        st.session_state.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if "telegram_chat_id" not in st.session_state:
        st.session_state.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram_message(text: str) -> tuple[bool, str]:
    """Send message via Telegram bot."""
    token = st.session_state.get("telegram_token", "")
    chat_id = st.session_state.get("telegram_chat_id", "")

    if not token or not chat_id:
        return False, "Telegram not configured"

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": text[:4096],  # Telegram limit
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True, "Sent"
            return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


def get_chat_response(message: str) -> str:
    """Get AI response for chat message."""
    try:
        client, ModelTier = get_api_client()

        # Build context from history
        messages = []
        for msg in st.session_state.chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        system_prompt = """You are Aether-Claw, a secure, swarm-based AI assistant.

Capabilities:
- Persistent memory (searchable brain files indexed in SQLite)
- Cryptographically signed skills with RSA-2048
- Proactive heartbeat tasks (git scanning, memory indexing, health checks)
- Swarm orchestration for parallel task execution
- Kill switch for immediate halt on security events
- Safety gate requiring confirmation for sensitive actions

Be helpful, security-conscious, and concise. When asked to perform tasks,
explain what you would do and ask for confirmation before taking action."""

        response = client.call(
            prompt=message,
            tier=ModelTier.TIER_1_REASONING,
            system_prompt=system_prompt
        )

        if response.success:
            return response.content
        return f"Error: {response.error}"

    except Exception as e:
        return f"Error connecting to AI: {e}"


def render_sidebar():
    """Render sidebar with status and controls."""
    with st.sidebar:
        st.title("🦅 Aether-Claw")
        st.caption("Secure Swarm-Based AI Assistant")
        st.divider()

        # Status
        st.subheader("📊 Status")
        status = get_system_status()

        if "error" in status:
            st.error(f"Error: {status['error']}")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Memory", status['indexed_files'])
                st.metric("Skills", f"{status['valid_skills']}/{status['skills']}")
            with col2:
                st.metric("Versions", status['total_versions'])
                st.metric("Heartbeat", f"{status['heartbeat_interval']}m")

            # Safety status
            st.divider()
            st.subheader("🔒 Security")

            safety = "🟢" if status['safety_gate'] else "🔴"
            st.markdown(f"Safety Gate: **{safety} {'ON' if status['safety_gate'] else 'OFF'}**")

            if status['kill_switch_triggered']:
                ks = "🔴 TRIGGERED"
            elif status['kill_switch_armed']:
                ks = "🟡 ARMED"
            else:
                ks = "🟢 READY"
            st.markdown(f"Kill Switch: **{ks}**")

        st.divider()

        # Quick Actions
        st.subheader("⚡ Actions")

        if st.button("▶ Run Heartbeat", use_container_width=True):
            with st.spinner("Running tasks..."):
                try:
                    from heartbeat_daemon import HeartbeatDaemon
                    daemon = HeartbeatDaemon()
                    results = daemon.run_once()
                    st.success(f"Completed {len(results)} tasks")
                    for r in results:
                        icon = "✅" if r.success else "❌"
                        st.text(f"{icon} {r.task_name}")
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.button("📁 Index Brain", use_container_width=True):
            with st.spinner("Indexing..."):
                try:
                    from brain_index import BrainIndexer
                    indexer = BrainIndexer()
                    results = indexer.index_all()
                    st.success(f"Indexed {len(results)} files")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()

        # Telegram Settings
        st.subheader("📱 Telegram")

        telegram_enabled = st.checkbox("Enable Telegram", value=st.session_state.telegram_enabled)
        st.session_state.telegram_enabled = telegram_enabled

        if telegram_enabled:
            token = st.text_input("Bot Token", value=st.session_state.telegram_token, type="password")
            chat_id = st.text_input("Chat ID", value=st.session_state.telegram_chat_id)

            st.session_state.telegram_token = token
            st.session_state.telegram_chat_id = chat_id

            if st.button("Test Connection", use_container_width=True):
                if token and chat_id:
                    success, msg = send_telegram_message("🦅 *Aether-Claw connected!*")
                    if success:
                        st.success("Telegram connected!")
                    else:
                        st.error(f"Failed: {msg}")
                else:
                    st.warning("Enter token and chat ID")


def render_chat():
    """Render chat interface."""
    st.header("💬 Chat with Aether-Claw")
    st.caption("Ask questions, run tasks, or explore your memory")

    # Display chat history
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Message Aether-Claw..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_chat_response(prompt)
                st.markdown(response)

                # Send to Telegram if enabled
                if st.session_state.telegram_enabled:
                    send_telegram_message(f"👤 *You:* {prompt}\n\n🦅 *Aether-Claw:*\n{response[:2000]}")

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()


def render_memory():
    """Render memory search interface."""
    st.header("🧠 Memory Search")
    st.caption("Search through indexed brain files")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input("Search", placeholder="Enter search query...", label_visibility="collapsed")

        if search_query:
            try:
                from brain_index import BrainIndexer
                indexer = BrainIndexer()
                results = indexer.search_memory(search_query, limit=10)

                if results:
                    st.success(f"Found {len(results)} results")
                    for r in results:
                        with st.expander(f"📄 {r['file_name']}"):
                            content = r.get('content', '')
                            st.text(content[:1500] + "..." if len(content) > 1500 else content)
                else:
                    st.info("No results found")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        st.subheader("Quick Access")
        brain_files = ["soul.md", "user.md", "memory.md", "heartbeat.md", "audit_log.md"]

        for f in brain_files:
            if st.button(f, key=f"brain_{f}", use_container_width=True):
                st.session_state.selected_brain_file = f

        st.divider()

        if "selected_brain_file" in st.session_state:
            file_path = Path(__file__).parent / "brain" / st.session_state.selected_brain_file
            if file_path.exists():
                with open(file_path) as f:
                    st.code(f.read()[:2000], language="markdown")


def render_skills():
    """Render skills management interface."""
    st.header("🔧 Skills")
    st.caption("Manage cryptographically signed skills")

    col1, col2 = st.columns([2, 1])

    with col1:
        try:
            from safe_skill_creator import SafeSkillCreator
            creator = SafeSkillCreator()
            skills = creator.list_skills()

            if skills:
                for skill in skills:
                    valid = skill.get('signature_valid', False)
                    status = "✅ Valid" if valid else "❌ Invalid"
                    color = "green" if valid else "red"

                    with st.container(border=True):
                        st.markdown(f"### {skill['name']}")
                        st.markdown(f"**Signature:** :{color}[{status}]")

                        meta = skill.get('metadata', {})
                        st.caption(f"Version: {meta.get('version', 'N/A')} | Created: {meta.get('created_at', 'N/A')[:10]}")

                        if st.button("View Code", key=f"view_{skill['name']}"):
                            st.code(skill.get('code', ''), language="python")
            else:
                st.info("No skills found. Create one with `aetherclaw sign-skill --create <file>`")

        except Exception as e:
            st.error(f"Error: {e}")

    with col2:
        st.subheader("Create Skill")

        skill_name = st.text_input("Skill Name")
        skill_code = st.text_area("Python Code", height=200)

        if st.button("Sign & Create", use_container_width=True, type="primary"):
            if skill_name and skill_code:
                try:
                    from safe_skill_creator import SafeSkillCreator
                    creator = SafeSkillCreator()

                    signed = creator.create_skill_from_code(
                        code=skill_code,
                        name=skill_name,
                        description=f"Skill created via dashboard"
                    )
                    path = creator.save_skill(signed)
                    st.success(f"Skill created: {path}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Enter name and code")


def render_swarm():
    """Render swarm orchestration interface."""
    st.header("🐝 Swarm Orchestration")
    st.caption("Execute tasks with parallel worker agents")

    col1, col2 = st.columns([2, 1])

    with col1:
        task_desc = st.text_area("Task Description", height=100, placeholder="Describe the task for the swarm...")

        if st.button("Execute Task", type="primary"):
            if task_desc:
                with st.spinner("Running swarm..."):
                    try:
                        from swarm.orchestrator import SwarmOrchestrator
                        from swarm.worker import Task

                        orchestrator = SwarmOrchestrator()
                        task = Task(
                            id=f"task-{datetime.now().strftime('%H%M%S')}",
                            description=task_desc
                        )
                        orchestrator.add_task(task)

                        results = orchestrator.run_until_complete()

                        for completed in results:
                            st.success(f"Task {completed.id} completed")
                            if completed.result:
                                st.json(completed.result)
                            if completed.error:
                                st.error(f"Error: {completed.error}")

                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Enter a task description")

    with col2:
        st.subheader("Swarm Status")

        try:
            from swarm.orchestrator import SwarmOrchestrator
            orchestrator = SwarmOrchestrator()
            status = orchestrator.monitor_progress()

            st.metric("Workers", status.total_workers)
            st.metric("Active", status.active_workers)
            st.metric("Pending", status.pending_tasks)
            st.metric("Completed", status.completed_tasks)
            st.metric("Failed", status.failed_tasks)
        except Exception as e:
            st.error(f"Error: {e}")


def render_logs():
    """Render audit logs."""
    st.header("📋 Audit Logs")
    st.caption("Immutable record of all system actions")

    audit_file = Path(__file__).parent / 'brain' / 'audit_log.md'

    if audit_file.exists():
        with open(audit_file) as f:
            content = f.read()

        # Parse entries
        entries = content.split('### ')[1:] if '### ' in content else []

        # Filter
        level_filter = st.multiselect(
            "Filter by level",
            ["INFO", "WARN", "ERROR", "SECURITY", "AUDIT"],
            default=["INFO", "WARN", "ERROR"]
        )

        for entry in entries[-50:]:
            header = entry.split('\n')[0]
            if any(f"| {level} |" in header for level in level_filter):
                if "| ERROR |" in header or "| SECURITY |" in header:
                    st.error(header)
                elif "| WARN |" in header:
                    st.warning(header)
                else:
                    st.info(header)

                with st.expander("Details"):
                    st.code("### " + entry[:1000], language="markdown")
    else:
        st.info("No audit log found")


def main():
    """Main dashboard."""
    init_session_state()
    render_sidebar()

    # Title
    st.title("🦅 Aether-Claw Dashboard")

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat", "🧠 Memory", "🔧 Skills", "🐝 Swarm", "📋 Logs"
    ])

    with tab1:
        render_chat()

    with tab2:
        render_memory()

    with tab3:
        render_skills()

    with tab4:
        render_swarm()

    with tab5:
        render_logs()


if __name__ == "__main__":
    main()
