import unittest

from services.finding_prioritizer import (
    build_priority_analysis,
    enrich_investigation_priorities,
    is_system_namespace,
    mentions_primary_issue,
)


class FindingPrioritizerTests(unittest.TestCase):
    def test_system_namespace_classification(self) -> None:
        self.assertTrue(is_system_namespace("kube-system"))
        self.assertTrue(is_system_namespace("local-path-storage"))
        self.assertFalse(is_system_namespace("default"))

    def test_user_workload_prioritized_over_system_restarts(self) -> None:
        investigation = {
            "pods": {
                "problematic_pods": [
                    {
                        "name": "kube-proxy-gbgnd",
                        "namespace": "kube-system",
                        "status": "High restart count (250)",
                        "phase": "Running",
                        "restart_count": 250,
                    },
                    {
                        "name": "nginx-crash",
                        "namespace": "default",
                        "status": "Error",
                        "phase": "Failed",
                        "container": "nginx-crash",
                        "terminated_reason": "Error",
                        "exit_code": 1,
                    },
                ]
            }
        }

        enrich_investigation_priorities(investigation)
        analysis = investigation["priority_analysis"]

        self.assertEqual(len(analysis["primary_user_findings"]), 1)
        self.assertEqual(analysis["primary_user_findings"][0]["name"], "nginx-crash")
        self.assertGreater(
            analysis["primary_user_findings"][0]["priority_score"],
            analysis["secondary_system_findings"][0]["priority_score"],
        )
        self.assertEqual(analysis["recommended_primary_issue"]["name"], "nginx-crash")
        self.assertEqual(investigation["pods"]["problematic_pods"][0]["name"], "nginx-crash")

    def test_mentions_primary_issue(self) -> None:
        primary = {"namespace": "default", "name": "nginx-crash"}
        self.assertTrue(mentions_primary_issue("default/nginx-crash failed", primary))
        self.assertFalse(mentions_primary_issue("kube-proxy restart loop", primary))


if __name__ == "__main__":
    unittest.main()
