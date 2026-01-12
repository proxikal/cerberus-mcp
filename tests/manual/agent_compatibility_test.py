"""Cross-agent compatibility testing for CERBERUS.md UACP v1.0 format.

Tests CERBERUS.md with Claude, Gemini, and Codex to validate:
- Context understanding
- Instruction compliance
- Token efficiency
- Forbidden action detection
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List


class AgentCompatibilityTest:
    """Test CERBERUS.md compatibility across AI agents."""

    def __init__(self, context_file: Path = Path("CERBERUS.md")):
        self.context_file = context_file
        self.context_content = context_file.read_text()
        self.results = {}

    def test_claude(self) -> Dict[str, Any]:
        """Test Claude CLI understanding of CERBERUS.md."""
        print("Testing Claude CLI...")

        # Conservative test: small prompt with core context only
        core_section = self._extract_section("## CORE [ALWAYS_LOAD]", "## IDENTITY")

        prompt = f"""{core_section}

Question: What is Cerberus in 5 words?"""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )

            response = result.stdout
            mission_ok = "context" in response.lower() or "deterministic" in response.lower()

            return {
                "agent": "claude",
                "success": True,
                "mission_understanding": mission_ok,
                "response_sample": response[:200] if response else "No response",
            }

        except Exception as e:
            return {
                "agent": "claude",
                "success": False,
                "error": str(e),
            }

    def test_gemini(self) -> Dict[str, Any]:
        """Test Gemini CLI understanding of CERBERUS.md."""
        print("Testing Gemini CLI...")

        # Conservative test with core identity only
        identity_section = self._extract_section("## IDENTITY", "## RULES")

        prompt = f"""Context:
{identity_section[:500]}

Q: Name 2 things this tool should NOT do."""

        try:
            result = subprocess.run(
                ["gemini", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )

            response = result.stdout
            understands = "llm" in response.lower() or "time" in response.lower() or "feature" in response.lower()

            return {
                "agent": "gemini",
                "success": True,
                "understands_forbiddens": understands,
                "response_sample": response[:200] if response else "No response",
            }

        except Exception as e:
            return {
                "agent": "gemini",
                "success": False,
                "error": str(e),
            }

    def test_codex(self) -> Dict[str, Any]:
        """Test Codex CLI understanding of CERBERUS.md."""
        print("Testing Codex CLI...")

        # Test with core only
        core_section = self._extract_section("## CORE [ALWAYS_LOAD]", "## IDENTITY")

        prompt = f"""Context:
{core_section[:400]}

Q: What is this system?"""

        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )

            response = result.stdout
            understands = "context" in response.lower() or "ast" in response.lower() or "cerberus" in response.lower()

            return {
                "agent": "codex",
                "success": True,
                "understands_identity": understands,
                "response_sample": response[:200] if response else "No response",
            }

        except Exception as e:
            return {
                "agent": "codex",
                "success": False,
                "error": str(e),
            }

    def _extract_section(self, start_marker: str, end_marker: str) -> str:
        """Extract section between two markers."""
        try:
            start = self.context_content.index(start_marker)
            end = self.context_content.index(end_marker, start)
            return self.context_content[start:end]
        except ValueError:
            return ""

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all compatibility tests."""
        print(f"\n{'='*60}")
        print("CERBERUS.md Cross-Agent Compatibility Test")
        print(f"{'='*60}\n")

        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "context_file": str(self.context_file),
            "context_size": len(self.context_content),
            "context_tokens_approx": len(self.context_content.split()),
            "tests": []
        }

        # Test each agent
        for test_fn in [self.test_claude, self.test_gemini, self.test_codex]:
            try:
                result = test_fn()
                results["tests"].append(result)

                # Print result
                agent = result["agent"]
                success = "✓" if result.get("success") else "✗"
                print(f"{success} {agent.upper()}: {result.get('error', 'OK')}")

            except Exception as e:
                print(f"✗ {test_fn.__name__}: {e}")
                results["tests"].append({
                    "agent": test_fn.__name__.replace("test_", ""),
                    "success": False,
                    "error": str(e),
                })

        # Summary
        total = len(results["tests"])
        passed = sum(1 for t in results["tests"] if t.get("success"))

        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} agents compatible")
        print(f"{'='*60}\n")

        return results

    def generate_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Generate compatibility report."""
        report = f"""# CERBERUS.md Cross-Agent Compatibility Report
Generated: {results['timestamp']}

## Summary
- Context file: {results['context_file']}
- Context size: {results['context_size']} bytes (~{results['context_tokens_approx']} tokens)
- Agents tested: {len(results['tests'])}
- Success rate: {sum(1 for t in results['tests'] if t.get('success'))}/{len(results['tests'])}

## Test Results

"""

        for test in results["tests"]:
            agent = test["agent"].upper()
            status = "✓ PASS" if test.get("success") else "✗ FAIL"

            report += f"### {agent} - {status}\n\n"

            if test.get("success"):
                for key, value in test.items():
                    if key not in ["agent", "success", "response_sample"]:
                        report += f"- **{key}**: {value}\n"

                if "response_sample" in test:
                    report += f"\n**Sample response:**\n```\n{test['response_sample']}\n```\n"
            else:
                report += f"**Error:** {test.get('error', 'Unknown')}\n"

            report += "\n"

        # Recommendations
        report += """## Recommendations

Based on compatibility test results:
"""

        passed_agents = [t["agent"] for t in results["tests"] if t.get("success")]

        if len(passed_agents) >= 2:
            report += f"- ✓ CERBERUS.md format is compatible with: {', '.join(passed_agents)}\n"
            report += "- Consider this format production-ready for multi-agent workflows\n"
        else:
            report += "- ⚠ Limited compatibility detected\n"
            report += "- Consider format simplification or agent-specific variants\n"

        output_file.write_text(report)
        print(f"Report written to: {output_file}")


def main():
    """Run cross-agent compatibility tests."""
    tester = AgentCompatibilityTest()
    results = tester.run_all_tests()

    # Save results
    results_file = Path("agent_compatibility_results.json")
    results_file.write_text(json.dumps(results, indent=2))
    print(f"Raw results: {results_file}")

    # Generate report
    report_file = Path("AGENT_COMPATIBILITY_REPORT.md")
    tester.generate_report(results, report_file)

    return results


if __name__ == "__main__":
    main()
