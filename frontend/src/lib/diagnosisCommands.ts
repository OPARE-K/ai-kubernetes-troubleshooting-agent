import type { Diagnosis } from "@/types/api";

export function getDiagnosisCommands(diagnosis: Diagnosis): string[] {
  const kubectlCommands = diagnosis.kubectl_commands;
  if (Array.isArray(kubectlCommands) && kubectlCommands.length > 0) {
    return kubectlCommands.map((command) => command.trim()).filter(Boolean);
  }

  const single =
    diagnosis.kubectl_command?.trim() ||
    diagnosis.command?.trim() ||
    "";
  if (!single) {
    return [];
  }

  if (single.includes("\n")) {
    return single
      .split("\n")
      .map((command) => command.trim())
      .filter(Boolean);
  }

  if (single.split("kubectl ").length > 2) {
    return single
      .split(/(?=kubectl )/)
      .map((command) => command.trim())
      .filter(Boolean);
  }

  return [single];
}
