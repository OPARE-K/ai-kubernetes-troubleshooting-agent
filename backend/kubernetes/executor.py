import json
import subprocess
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class KubectlResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    command: str

    def json_output(self) -> dict[str, Any] | list[Any] | None:
        if not self.stdout.strip():
            return None
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError:
            logger.warning("Failed to parse kubectl JSON output")
            return None


class KubectlExecutor:
    """Safely execute kubectl commands and return structured output."""

    def __init__(self, kubeconfig_path: str = "", context: str = "") -> None:
        self.kubeconfig_path = kubeconfig_path
        self.context = context

    def run(self, *args: str, timeout: int = 60) -> KubectlResult:
        command = ["kubectl"]
        if self.kubeconfig_path:
            command.extend(["--kubeconfig", self.kubeconfig_path])
        if self.context:
            command.extend(["--context", self.context])
        command.extend(args)
        command_str = " ".join(command)

        logger.info(f"Running kubectl command: {command_str}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            logger.error("kubectl binary not found in PATH")
            return KubectlResult(
                success=False,
                stdout="",
                stderr="kubectl not found. Ensure kubectl is installed and in PATH.",
                return_code=127,
                command=command_str,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl command timed out after {timeout}s: {command_str}")
            return KubectlResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds.",
                return_code=124,
                command=command_str,
            )

        kubectl_result = KubectlResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            command=command_str,
        )

        if kubectl_result.success:
            logger.info(f"kubectl command succeeded: {command_str}")
        else:
            logger.warning(
                f"kubectl command failed (exit {result.returncode}): {command_str}"
            )
            if result.stderr:
                logger.warning(f"kubectl stderr: {result.stderr.strip()}")

        return kubectl_result
