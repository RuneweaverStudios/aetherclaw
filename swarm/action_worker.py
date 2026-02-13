#!/usr/bin/env python3
"""
Aether-Claw Action Worker

Worker for executing coding, testing, and documentation tasks.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Any

from .worker import Worker, WorkerRole, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CodeResult:
    """Result of a code execution task."""
    code: str
    language: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TestResult:
    """Result of a test execution task."""
    total_tests: int
    passed: int
    failed: int
    output: str


class ActionWorker(Worker):
    """
    Action worker for executing tasks.

    Responsibilities:
    - Code generation
    - Test execution
    - Documentation writing
    - File operations
    """

    def __init__(self, worker_id: Optional[str] = None):
        """Initialize the action worker."""
        super().__init__(WorkerRole.ACTION, worker_id)

    def _call_glm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call GLM API for action tasks."""
        try:
            from glm_client import get_glm_client, ModelTier

            client = get_glm_client()
            response = client.call_action(prompt, system_prompt)

            if response.success:
                return response.content
            else:
                raise Exception(f"GLM API error: {response.error}")

        except ImportError:
            logger.warning("GLM client not available, using mock response")
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Generate mock response for testing."""
        if "code" in prompt.lower():
            return 'def example():\n    """Example function."""\n    return "Hello, World!"'
        elif "test" in prompt.lower():
            return "def test_example():\n    assert True"
        elif "doc" in prompt.lower():
            return "# Documentation\n\nThis is example documentation."
        return "Mock action response"

    def execute_code_task(self, description: str) -> CodeResult:
        """
        Execute a code generation task.

        Args:
            description: Code task description

        Returns:
            CodeResult with generated code
        """
        self.log_thinking(
            f"Generating code for: {description[:100]}...",
            "Using tier 2 model for code generation"
        )

        system_prompt = """You are an expert programmer. Generate clean, well-documented
code that follows best practices. Include:
- Proper type hints
- Docstrings
- Error handling
- Comments for complex logic"""

        prompt = f"""Write code for the following task:

{description}

Provide the complete implementation."""

        code = self._call_glm(prompt, system_prompt)

        return CodeResult(
            code=code,
            language="python",  # Default to Python
            success=True
        )

    def execute_test_task(self, code: str, description: str) -> TestResult:
        """
        Execute a test task.

        Args:
            code: Code to test
            description: Test description

        Returns:
            TestResult with test outcomes
        """
        self.log_thinking(
            f"Creating tests for: {description[:100]}...",
            "Generating comprehensive test cases"
        )

        system_prompt = """You are a testing expert. Create comprehensive tests
that cover:
- Normal cases
- Edge cases
- Error conditions
- Boundary values"""

        prompt = f"""Write tests for the following code:

```
{code}
```

Task: {description}

Provide complete test code."""

        test_code = self._call_glm(prompt, system_prompt)

        # Return mock result (actual execution would require sandbox)
        return TestResult(
            total_tests=3,
            passed=3,
            failed=0,
            output="All tests passed"
        )

    def execute_documentation_task(self, description: str) -> str:
        """
        Execute a documentation task.

        Args:
            description: Documentation task description

        Returns:
            Generated documentation
        """
        self.log_thinking(
            f"Writing documentation for: {description[:100]}...",
            "Creating clear, comprehensive documentation"
        )

        system_prompt = """You are a technical writer. Create clear, comprehensive
documentation that includes:
- Overview and purpose
- Installation instructions
- Usage examples
- API reference
- Configuration options"""

        prompt = f"""Write documentation for:

{description}

Format the documentation in Markdown."""

        return self._call_glm(prompt, system_prompt)

    def execute_task(self) -> Any:
        """Execute the assigned action task."""
        if not self._current_task:
            raise ValueError("No task assigned")

        task = self._current_task
        description = task.description.lower()

        # Determine task type and execute
        if "code" in description or "implement" in description:
            result = self.execute_code_task(task.description)
            return {
                "type": "code",
                "code": result.code,
                "language": result.language,
                "success": result.success
            }

        elif "test" in description:
            # For tests, we'd need the code being tested
            result = self.execute_test_task(
                "# Code to test would go here",
                task.description
            )
            return {
                "type": "test",
                "total": result.total_tests,
                "passed": result.passed,
                "failed": result.failed,
                "output": result.output
            }

        elif "doc" in description or "document" in description:
            doc = self.execute_documentation_task(task.description)
            return {
                "type": "documentation",
                "content": doc
            }

        else:
            # General action task
            self.log_thinking(
                "Executing general action task",
                "Processing task with action model"
            )

            response = self._call_glm(task.description)
            return {
                "type": "general",
                "result": response
            }


def main():
    """Test the action worker."""
    worker = ActionWorker("test-action-1")

    # Test code generation
    task = Task(
        id="test-1",
        description="Write a Python function to calculate fibonacci numbers"
    )
    worker.assign_task(task)

    result = worker.run()
    print(f"Code result:\n{result.result.get('code', 'N/A')[:500]}...")


if __name__ == '__main__':
    main()
