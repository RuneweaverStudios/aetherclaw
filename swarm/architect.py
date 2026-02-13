#!/usr/bin/env python3
"""
Aether-Claw Architect Worker

High-level reasoning worker for problem decomposition and security review.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Any

from .worker import Worker, WorkerRole, WorkerStatus, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SecurityRisk:
    """Represents a security risk found in assessment."""
    category: str
    severity: str  # low, medium, high, critical
    description: str
    recommendation: str


@dataclass
class DecompositionResult:
    """Result of problem decomposition."""
    subtasks: list[dict]
    dependencies: list[tuple[str, str]]
    estimated_complexity: str  # low, medium, high


class Architect(Worker):
    """
    Architect worker for high-level reasoning tasks.

    Responsibilities:
    - Problem decomposition
    - Security assessment
    - Architectural planning
    - Task prioritization
    """

    def __init__(self, worker_id: Optional[str] = None):
        """Initialize the architect worker."""
        super().__init__(WorkerRole.ARCHITECT, worker_id)

    def _call_glm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call GLM API for reasoning."""
        try:
            from glm_client import get_glm_client, ModelTier

            client = get_glm_client()
            response = client.call_reasoning(prompt, system_prompt)

            if response.success:
                return response.content
            else:
                raise Exception(f"GLM API error: {response.error}")

        except ImportError:
            # Fallback for testing without GLM client
            logger.warning("GLM client not available, using mock response")
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Generate mock response for testing."""
        if "decompose" in prompt.lower():
            return json.dumps({
                "subtasks": [
                    {"id": "subtask-1", "description": "First subtask"},
                    {"id": "subtask-2", "description": "Second subtask"}
                ],
                "dependencies": [],
                "complexity": "medium"
            })
        elif "security" in prompt.lower():
            return json.dumps({
                "risks": [],
                "overall_risk": "low"
            })
        return "Mock response"

    def decompose_problem(self, description: str) -> DecompositionResult:
        """
        Decompose a complex problem into subtasks.

        Args:
            description: Problem description

        Returns:
            DecompositionResult with subtasks
        """
        self.log_thinking(
            f"Analyzing problem for decomposition: {description[:100]}...",
            "Breaking down into manageable subtasks"
        )

        system_prompt = """You are an expert software architect. Your job is to decompose
complex tasks into smaller, manageable subtasks. Each subtask should be:
1. Independently executable
2. Clearly defined with acceptance criteria
3. Properly sequenced with dependencies identified

Respond in JSON format with:
{
    "subtasks": [{"id": "ST-1", "description": "...", "priority": 1}],
    "dependencies": [["ST-1", "ST-2"]],
    "complexity": "low|medium|high"
}"""

        prompt = f"""Decompose the following task into subtasks:

{description}

Provide a structured breakdown with IDs, descriptions, priorities, and dependencies."""

        response = self._call_glm(prompt, system_prompt)

        try:
            data = json.loads(response)
            return DecompositionResult(
                subtasks=data.get('subtasks', []),
                dependencies=[tuple(d) for d in data.get('dependencies', [])],
                estimated_complexity=data.get('complexity', 'medium')
            )
        except json.JSONDecodeError:
            # Fallback parsing
            return DecompositionResult(
                subtasks=[{"id": "main", "description": description}],
                dependencies=[],
                estimated_complexity="medium"
            )

    def security_assessment(self, code_or_task: str) -> list[SecurityRisk]:
        """
        Perform security assessment on code or task.

        Args:
            code_or_task: Code or task description to assess

        Returns:
            List of SecurityRisk objects
        """
        self.log_thinking(
            f"Performing security assessment on: {code_or_task[:100]}...",
            "Checking for potential vulnerabilities"
        )

        system_prompt = """You are a security expert. Analyze the given code or task
for security risks. Consider:
- Input validation issues
- Authentication/authorization flaws
- Data exposure risks
- Injection vulnerabilities
- Resource management issues

Respond in JSON format with:
{
    "risks": [
        {
            "category": "category",
            "severity": "low|medium|high|critical",
            "description": "description",
            "recommendation": "how to fix"
        }
    ],
    "overall_risk": "low|medium|high|critical"
}"""

        prompt = f"""Perform a security assessment on:

{code_or_task}

Identify potential security risks and provide recommendations."""

        response = self._call_glm(prompt, system_prompt)

        risks = []
        try:
            data = json.loads(response)
            for risk_data in data.get('risks', []):
                risks.append(SecurityRisk(
                    category=risk_data.get('category', 'unknown'),
                    severity=risk_data.get('severity', 'low'),
                    description=risk_data.get('description', ''),
                    recommendation=risk_data.get('recommendation', '')
                ))
        except json.JSONDecodeError:
            pass

        return risks

    def align_with_goals(self, task: Task, goals: list[str]) -> float:
        """
        Check if a task aligns with defined goals.

        Args:
            task: Task to check
            goals: List of goals from soul.md

        Returns:
            Alignment score (0.0 to 1.0)
        """
        self.log_thinking(
            f"Checking alignment of task {task.id} with {len(goals)} goals",
            "Calculating alignment score"
        )

        # Simple keyword matching for now
        task_words = set(task.description.lower().split())
        goal_words = set(' '.join(goals).lower().split())

        common = task_words & goal_words
        if not task_words:
            return 0.0

        return len(common) / min(len(task_words), 10)  # Cap at reasonable level

    def execute_task(self) -> Any:
        """Execute the assigned architect task."""
        if not self._current_task:
            raise ValueError("No task assigned")

        task = self._current_task
        description = task.description

        # Determine task type and execute
        if "decompose" in description.lower():
            result = self.decompose_problem(description)
            return {
                "type": "decomposition",
                "subtasks": result.subtasks,
                "dependencies": result.dependencies,
                "complexity": result.estimated_complexity
            }

        elif "security" in description.lower() or "assess" in description.lower():
            risks = self.security_assessment(description)
            return {
                "type": "security_assessment",
                "risks": [{"category": r.category, "severity": r.severity,
                          "description": r.description, "recommendation": r.recommendation}
                         for r in risks],
                "risk_count": len(risks)
            }

        else:
            # General architectural review
            self.log_thinking(
                "Performing general architectural review",
                "Analyzing task requirements and structure"
            )

            return {
                "type": "architectural_review",
                "description": description,
                "recommendations": ["Review requirements", "Design solution", "Implement"]
            }


def main():
    """Test the architect worker."""
    architect = Architect("test-arch-1")

    # Test decomposition
    task = Task(
        id="test-1",
        description="Decompose the task of building a REST API for user management"
    )
    architect.assign_task(task)

    result = architect.run()
    print(f"Task completed: {result.result}")

    # Test security assessment
    task2 = Task(
        id="test-2",
        description="Assess security of: execute_query(user_input)"
    )

    architect.assign_task(task2)
    result2 = architect.run()
    print(f"Security risks found: {result2.result.get('risk_count', 0)}")


if __name__ == '__main__':
    main()
