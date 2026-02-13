"""
CLI integration for DevLibrary Evaluator Plugin

Provides command-line interface integration with the AAS CLI system
for running evaluations and generating reports.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import click
import json

from loguru import logger
from core.managers import ManagerHub
from .evaluator import DevLibraryEvaluatorPlugin, EvaluationConfig


class DevLibraryEvaluatorCLI:
    """CLI handler for DevLibrary evaluation commands"""

    def __init__(self, manager_hub: ManagerHub):
        self.manager_hub = manager_hub
        self.logger = getattr(manager_hub, "logger", logger)
        self.evaluator = DevLibraryEvaluatorPlugin(manager_hub)

    async def run_evaluation(
        self,
        workspace_path: str,
        analyzers: Optional[List[str]] = None,
        output_format: str = "markdown",
        output_path: Optional[str] = None,
        quick_mode: bool = False,
        include_tasks: bool = True,
        summary_only: bool = False,
    ) -> int:
        """
        Run DevLibrary evaluation

        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Validate workspace path
            workspace = Path(workspace_path).resolve()
            if not workspace.exists():
                self.logger.error(f"Workspace path does not exist: {workspace}")
                return 1

            # Create evaluation configuration
            config = EvaluationConfig(
                workspace_path=workspace,
                analyzers=analyzers,
                output_format=output_format,
                output_path=Path(output_path) if output_path else None,
                quick_mode=quick_mode,
                include_tasks=include_tasks,
            )

            self.logger.info(f"Starting DevLibrary evaluation: {workspace}")

            if quick_mode:
                # Run quick evaluation
                results = await self.evaluator.quick_evaluate(workspace)
                self._print_quick_results(results, summary_only)
            else:
                # Run full evaluation
                report = await self.evaluator.evaluate_workspace(config)
                self._print_full_results(report, summary_only, output_format)

                # Save report if output path specified
                if output_path:
                    await self._save_report(report, Path(output_path), output_format)

            self.logger.info("DevLibrary evaluation completed successfully")
            return 0

        except Exception as e:
            self.logger.error(f"Evaluation failed: {str(e)}")
            return 1

    def _print_quick_results(self, results: Dict[str, Any], summary_only: bool):
        """Print quick evaluation results to console"""
        print("\n" + "=" * 60)
        print("DEVLIBRARY QUICK EVALUATION RESULTS")
        print("=" * 60)

        # Executive summary
        if "summary" in results:
            print("\nSUMMARY:")
            print(results["summary"])

        # Strategic alignment
        if "strategic_alignment" in results and not summary_only:
            print("\nSTRATEGIC ALIGNMENT:")
            alignment = results["strategic_alignment"]
            if alignment:
                print(f"  Overall Score: {alignment.get('overall_score', 'N/A')}")
                print(
                    f"  Aligned Phases: {', '.join(alignment.get('aligned_phases', []))}"
                )

        # Top recommendations
        if "top_recommendations" in results:
            print("\nTOP RECOMMENDATIONS:")
            for i, rec in enumerate(results["top_recommendations"], 1):
                print(
                    f"  {i}. {rec.title} ({rec.priority} priority, {rec.effort} effort)"
                )
                if not summary_only:
                    print(f"     {rec.description[:100]}...")

        # Quick wins
        if "quick_wins" in results and results["quick_wins"]:
            print("\nQUICK WINS:")
            for i, rec in enumerate(results["quick_wins"], 1):
                print(f"  {i}. {rec.title}")
                if not summary_only:
                    print(f"     {rec.description[:80]}...")

        print("\n" + "=" * 60)

    def _print_full_results(self, report, summary_only: bool, output_format: str):
        """Print full evaluation results to console"""
        print("\n" + "=" * 60)
        print("DEVLIBRARY EVALUATION RESULTS")
        print("=" * 60)

        # Executive summary
        print("\nEXECUTIVE SUMMARY:")
        print(report.executive_summary)

        if not summary_only:
            # Projects analyzed
            print(f"\nPROJECTS ANALYZED: {len(report.analysis_results.projects)}")
            for project in report.analysis_results.projects:
                print(f"  - {project.name} ({project.language})")
                print(f"    Integration: {project.get_integration_level()}")
                print(f"    Priority: {project.get_strategic_priority()}")

            # Key findings by analyzer
            print("\nKEY FINDINGS:")
            self._print_analyzer_findings(report.analysis_results)

        # Recommendations
        print(f"\nRECOMMENDATIONS ({len(report.recommendations)} total):")
        for i, rec in enumerate(report.recommendations[:10], 1):  # Top 10
            print(f"  {i}. {rec.title}")
            print(f"     Priority: {rec.priority}, Effort: {rec.effort}")
            print(f"     Phase: {rec.roadmap_phase}")
            if not summary_only:
                print(f"     {rec.description[:100]}...")
            print()

        if len(report.recommendations) > 10:
            print(f"  ... and {len(report.recommendations) - 10} more recommendations")

        print("=" * 60)

    def _print_analyzer_findings(self, analysis_results):
        """Print findings from each analyzer"""
        analyzers = [
            ("architecture", "Architecture"),
            ("feature_gaps", "Feature Gaps"),
            ("integration", "Integration"),
            ("technical_debt", "Technical Debt"),
            ("strategic_alignment", "Strategic Alignment"),
            ("synergy", "Synergy"),
            ("workflow", "Workflow"),
        ]

        for analyzer_key, analyzer_name in analyzers:
            results = getattr(analysis_results, f"{analyzer_key}_results", None)
            if results and results.findings:
                print(f"\n  {analyzer_name}:")

                # Count by severity
                severity_counts = {}
                for finding in results.findings:
                    severity = finding.get("severity", "info")
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                severity_summary = []
                for severity in ["critical", "high", "medium", "low", "info"]:
                    if severity in severity_counts:
                        severity_summary.append(
                            f"{severity_counts[severity]} {severity}"
                        )

                print(f"    {', '.join(severity_summary)}")

                # Show top critical/high findings
                critical_findings = [
                    f
                    for f in results.findings
                    if f.get("severity") in ["critical", "high"]
                ][:3]

                for finding in critical_findings:
                    print(f"    - {finding['title']} ({finding['severity']})")

    async def _save_report(self, report, output_path: Path, output_format: str):
        """Save evaluation report to file"""
        try:
            if output_format.lower() == "json":
                # Save as JSON
                report_data = {
                    "executive_summary": report.executive_summary,
                    "projects": [p.to_dict() for p in report.analysis_results.projects],
                    "recommendations": [
                        {
                            "id": r.id,
                            "title": r.title,
                            "description": r.description,
                            "category": r.category,
                            "priority": r.priority,
                            "effort": r.effort,
                            "roadmap_phase": r.roadmap_phase,
                            "aas_task_id": r.aas_task_id,
                        }
                        for r in report.recommendations
                    ],
                    "timestamp": report.analysis_results.analysis_timestamp.isoformat(),
                }

                with open(output_path, "w") as f:
                    json.dump(report_data, f, indent=2)

            elif output_format.lower() in ["markdown", "md"]:
                # Save as Markdown (this would be implemented by report_generator)
                markdown_content = (
                    await self.evaluator.report_generator.generate_markdown(report)
                )
                with open(output_path, "w") as f:
                    f.write(markdown_content)

            elif output_format.lower() == "html":
                # Save as HTML (this would be implemented by report_generator)
                html_content = await self.evaluator.report_generator.generate_html(
                    report
                )
                with open(output_path, "w") as f:
                    f.write(html_content)

            else:
                raise ValueError(f"Unsupported output format: {output_format}")

            self.logger.info(f"Report saved to: {output_path}")

        except Exception as e:
            self.logger.error(f"Failed to save report: {str(e)}")
            raise


# CLI command registration for AAS CLI system
def register_cli_commands(cli_group, manager_hub: ManagerHub):
    """Register DevLibrary evaluator commands with AAS CLI"""

    evaluator_cli = DevLibraryEvaluatorCLI(manager_hub)

    @cli_group.command("evaluate")
    @click.option(
        "--workspace",
        "-w",
        default=".",
        help="Path to DevLibrary workspace (default: current directory)",
    )
    @click.option(
        "--analyzers",
        "-a",
        help="Comma-separated list of analyzers to run (default: all)",
    )
    @click.option(
        "--format",
        "-f",
        default="markdown",
        type=click.Choice(["markdown", "html", "json"]),
        help="Output format (default: markdown)",
    )
    @click.option("--output", "-o", help="Output file path (default: print to console)")
    @click.option(
        "--quick", is_flag=True, help="Run quick evaluation with limited analysis"
    )
    @click.option(
        "--no-tasks", is_flag=True, help="Don't create AAS tasks from recommendations"
    )
    @click.option("--summary-only", is_flag=True, help="Show only summary information")
    def evaluate_command(
        workspace, analyzers, format, output, quick, no_tasks, summary_only
    ):
        """Evaluate DevLibrary workspace and generate improvement recommendations"""

        # Parse analyzers list
        analyzer_list = None
        if analyzers:
            analyzer_list = [a.strip() for a in analyzers.split(",")]

        # Run evaluation
        exit_code = asyncio.run(
            evaluator_cli.run_evaluation(
                workspace_path=workspace,
                analyzers=analyzer_list,
                output_format=format,
                output_path=output,
                quick_mode=quick,
                include_tasks=not no_tasks,
                summary_only=summary_only,
            )
        )

        sys.exit(exit_code)

    @cli_group.command("evaluate-quick")
    @click.option(
        "--workspace",
        "-w",
        default=".",
        help="Path to DevLibrary workspace (default: current directory)",
    )
    def evaluate_quick_command(workspace):
        """Run quick DevLibrary evaluation with summary results"""

        exit_code = asyncio.run(
            evaluator_cli.run_evaluation(
                workspace_path=workspace,
                quick_mode=True,
                include_tasks=False,
                summary_only=True,
            )
        )

        sys.exit(exit_code)


def main():
    """Entrypoint for direct CLI usage via plugin manifest."""
    manager_hub = ManagerHub.create()

    @click.group()
    def cli_group():
        """DevLibrary evaluator commands."""
        pass

    register_cli_commands(cli_group, manager_hub)
    cli_group()


if __name__ == "__main__":
    main()
