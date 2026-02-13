#!/usr/bin/env python3
"""
Aether-Claw Configuration Loader

Loads and validates configuration from swarm_config.json.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_FILE = Path(__file__).parent / 'swarm_config.json'


@dataclass
class ModelRouting:
    """Model routing configuration."""
    endpoint: str
    model: str
    use_cases: list[str]
    max_tokens: int = 2048
    temperature: float = 0.5


@dataclass
class SafetyGateConfig:
    """Safety gate configuration."""
    enabled: bool = True
    confirmation_required: dict[str, bool] = field(default_factory=dict)
    auto_approve: dict[str, bool] = field(default_factory=dict)
    timeout_seconds: int = 300
    max_retries: int = 3


@dataclass
class KillSwitchTrigger:
    """Kill switch trigger configuration."""
    threshold: Optional[int] = None
    duration_seconds: Optional[int] = None
    action: str = "immediate"


@dataclass
class KillSwitchConfig:
    """Kill switch configuration."""
    enabled: bool = True
    triggers: dict[str, Any] = field(default_factory=dict)
    recovery_mode: str = "manual"


@dataclass
class SwarmConfig:
    """Swarm orchestration configuration."""
    max_workers: int = 3
    isolation_mode: str = "docker"
    worktree_prefix: str = "aether-worker"


@dataclass
class HeartbeatConfig:
    """Heartbeat configuration."""
    enabled: bool = True
    interval_minutes: int = 30
    config_file: str = "brain/heartbeat.md"
    notification_library: str = "plyer"


@dataclass
class Config:
    """Main configuration container."""
    version: str = "1.0.0"
    system_name: str = "Aether-Claw"
    model_routing: dict[str, ModelRouting] = field(default_factory=dict)
    safety_gate: SafetyGateConfig = field(default_factory=SafetyGateConfig)
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    brain_dir: str = "brain"
    skills_dir: str = "skills"
    log_file: str = "aether_claw.log"


class ConfigLoader:
    """Loads and validates configuration from JSON file."""

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the configuration loader.

        Args:
            config_file: Path to the configuration file
        """
        self.config_file = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
        self._config: Optional[Config] = None
        self._raw_config: Optional[dict] = None

    def load(self) -> Config:
        """
        Load configuration from file.

        Returns:
            Config object with loaded settings

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_file.exists():
            logger.warning(
                f"Config file not found: {self.config_file}. Using defaults."
            )
            return self._get_defaults()

        with open(self.config_file, 'r', encoding='utf-8') as f:
            self._raw_config = json.load(f)

        self._config = self._parse_config(self._raw_config)
        logger.info(f"Configuration loaded from {self.config_file}")

        return self._config

    def _get_defaults(self) -> Config:
        """Get default configuration."""
        return Config(
            model_routing={
                'tier_1_reasoning': ModelRouting(
                    endpoint="http://localhost:8081",
                    model="GLM-4.7",
                    use_cases=["reasoning", "planning"],
                    max_tokens=4096,
                    temperature=0.3
                ),
                'tier_2_action': ModelRouting(
                    endpoint="http://localhost:8082",
                    model="GLM-4.7-Flash",
                    use_cases=["action", "testing"],
                    max_tokens=2048,
                    temperature=0.5
                )
            },
            safety_gate=SafetyGateConfig(
                enabled=True,
                confirmation_required={
                    'file_write': True,
                    'network_request': True,
                    'system_command': True
                },
                auto_approve={
                    'file_read': True
                }
            )
        )

    def _parse_config(self, raw: dict) -> Config:
        """Parse raw config dictionary into Config object."""
        # Parse model routing
        model_routing = {}
        for tier, routing in raw.get('model_routing', {}).items():
            model_routing[tier] = ModelRouting(
                endpoint=routing.get('endpoint', 'http://localhost:8081'),
                model=routing.get('model', 'GLM-4.7'),
                use_cases=routing.get('use_cases', []),
                max_tokens=routing.get('max_tokens', 2048),
                temperature=routing.get('temperature', 0.5)
            )

        # Parse safety gate
        sg = raw.get('safety_gate', {})
        safety_gate = SafetyGateConfig(
            enabled=sg.get('enabled', True),
            confirmation_required=sg.get('confirmation_required', {}),
            auto_approve=sg.get('auto_approve', {}),
            timeout_seconds=sg.get('timeout_seconds', 300),
            max_retries=sg.get('max_retries', 3)
        )

        # Parse kill switch
        ks = raw.get('kill_switch', {})
        kill_switch = KillSwitchConfig(
            enabled=ks.get('enabled', True),
            triggers=ks.get('triggers', {}),
            recovery_mode=ks.get('recovery_mode', 'manual')
        )

        # Parse swarm
        sw = raw.get('swarm_orchestration', {})
        swarm = SwarmConfig(
            max_workers=sw.get('max_workers', 3),
            isolation_mode=sw.get('isolation_mode', 'docker'),
            worktree_prefix=sw.get('worktree_prefix', 'aether-worker')
        )

        # Parse heartbeat
        hb = raw.get('heartbeat', {})
        heartbeat = HeartbeatConfig(
            enabled=hb.get('enabled', True),
            interval_minutes=hb.get('interval_minutes', 30),
            config_file=hb.get('config_file', 'brain/heartbeat.md'),
            notification_library=hb.get('notification_library', 'plyer')
        )

        # Parse brain config
        brain = raw.get('brain', {})

        # Parse skills config
        skills = raw.get('skills', {})

        return Config(
            version=raw.get('version', '1.0.0'),
            system_name=raw.get('system_name', 'Aether-Claw'),
            model_routing=model_routing,
            safety_gate=safety_gate,
            kill_switch=kill_switch,
            swarm=swarm,
            heartbeat=heartbeat,
            brain_dir=brain.get('directory', 'brain'),
            skills_dir=skills.get('directory', 'skills'),
            log_file=raw.get('logging', {}).get('file', 'aether_claw.log')
        )

    def get_config(self) -> Config:
        """
        Get loaded configuration, loading if necessary.

        Returns:
            Config object
        """
        if self._config is None:
            return self.load()
        return self._config

    def get_model_routing(self, tier: str = 'tier_1_reasoning') -> ModelRouting:
        """
        Get model routing for a specific tier.

        Args:
            tier: Tier name (tier_1_reasoning or tier_2_action)

        Returns:
            ModelRouting configuration
        """
        config = self.get_config()
        return config.model_routing.get(tier, ModelRouting(
            endpoint="http://localhost:8081",
            model="GLM-4.7",
            use_cases=[]
        ))

    def requires_confirmation(self, action_type: str) -> bool:
        """
        Check if an action type requires user confirmation.

        Args:
            action_type: Type of action to check

        Returns:
            True if confirmation is required
        """
        config = self.get_config()

        if not config.safety_gate.enabled:
            return False

        # Check auto-approve first
        if config.safety_gate.auto_approve.get(action_type, False):
            return False

        # Check confirmation required
        return config.safety_gate.confirmation_required.get(action_type, True)

    def get_kill_switch_triggers(self) -> dict[str, Any]:
        """
        Get kill switch trigger configuration.

        Returns:
            Dictionary of trigger configurations
        """
        config = self.get_config()
        return config.kill_switch.triggers

    def is_kill_switch_enabled(self) -> bool:
        """Check if kill switch is enabled."""
        return self.get_config().kill_switch.enabled

    def get_heartbeat_interval(self) -> int:
        """Get heartbeat interval in minutes."""
        return self.get_config().heartbeat.interval_minutes

    def get_max_workers(self) -> int:
        """Get maximum number of workers."""
        return self.get_config().swarm.max_workers

    def reload(self) -> Config:
        """Reload configuration from file."""
        self._config = None
        return self.load()


# Global instance for convenience
_global_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get the global config loader instance."""
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
    return _global_loader


def load_config() -> Config:
    """Load configuration using global loader."""
    return get_config_loader().get_config()


def requires_confirmation(action_type: str) -> bool:
    """Check if action requires confirmation using global config."""
    return get_config_loader().requires_confirmation(action_type)


def main():
    """CLI entry point for config loader."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Config Loader')
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show current configuration'
    )
    parser.add_argument(
        '--check',
        type=str,
        help='Check if action requires confirmation'
    )
    parser.add_argument(
        '--tier',
        type=str,
        default='tier_1_reasoning',
        help='Get model routing for tier'
    )

    args = parser.parse_args()

    loader = ConfigLoader()

    if args.show:
        config = loader.get_config()
        print(f"Configuration ({config.system_name} v{config.version}):")
        print(f"  Brain directory: {config.brain_dir}")
        print(f"  Skills directory: {config.skills_dir}")
        print(f"  Max workers: {config.swarm.max_workers}")
        print(f"  Heartbeat interval: {config.heartbeat.interval_minutes} min")
        print(f"  Kill switch enabled: {config.kill_switch.enabled}")
        print(f"  Safety gate enabled: {config.safety_gate.enabled}")
        print("\nModel Routing:")
        for tier, routing in config.model_routing.items():
            print(f"  {tier}:")
            print(f"    Endpoint: {routing.endpoint}")
            print(f"    Model: {routing.model}")

    elif args.check:
        requires = loader.requires_confirmation(args.check)
        print(f"Action '{args.check}' requires confirmation: {requires}")

    elif args.tier:
        routing = loader.get_model_routing(args.tier)
        print(f"Model routing for {args.tier}:")
        print(f"  Endpoint: {routing.endpoint}")
        print(f"  Model: {routing.model}")
        print(f"  Max tokens: {routing.max_tokens}")
        print(f"  Temperature: {routing.temperature}")
        print(f"  Use cases: {', '.join(routing.use_cases)}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
