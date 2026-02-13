"""
Report generation for DevLibrary evaluation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from .models.analysis import EvaluationReport, AnalysisResults


class ReportGenerator:
    """Create evaluation reports from analysis and recommendations."""

    def __init__(self, manager_hub: Any):
        self.manager_hub = manager_hub
        self.logger = getattr(manager_hub, "logger", None)

    def _collect_analyzer_results(self, analysis_results: AnalysisResults) -> List[Any]:
        return [
            analysis_results.architecture_results,
            analysis_results.feature_gaps_results,
            analysis_results.integration_results,
            analysis_results.technical_debt_results,
            analysis_results.strategic_alignment_results,
            analysis_results.synergy_results,
            analysis_results.workflow_results,
        ]

    def _summarize_findings(
        self, analysis_results: AnalysisResults
    ) -> Tuple[Counter, List[Dict[str, Any]]]:
        severity_counts: Counter = Counter()
        findings: List[Dict[str, Any]] = []
        for result in self._collect_analyzer_results(analysis_results):
            if not result:
                continue
            for finding in result.findings or []:
                severity = (finding.get("severity") or "info").lower()
                severity_counts[severity] += 1
                findings.append(finding)
        return severity_counts, findings

    def _summarize_projects(
        self, analysis_results: AnalysisResults
    ) -> Dict[str, Counter]:
        integration_counts: Counter = Counter()
        priority_counts: Counter = Counter()
        language_counts: Counter = Counter()
        for project in analysis_results.projects:
            integration_counts[project.get_integration_level()] += 1
            priority_counts[project.get_strategic_priority()] += 1
            language_counts[project.language] += 1
        return {
            "integration": integration_counts,
            "priority": priority_counts,
            "language": language_counts,
        }

    def _format_counter(self, counter: Counter) -> str:
        if not counter:
            return "none"
        return ", ".join(f"{key}: {count}" for key, count in counter.items())

    def _build_executive_summary(
        self, analysis_results: AnalysisResults, recommendations: List[Any]
    ) -> str:
        project_total = len(analysis_results.projects)
        analyzers_run = sum(
            1
            for result in self._collect_analyzer_results(analysis_results)
            if result is not None
        )
        severity_counts, _ = self._summarize_findings(analysis_results)
        project_summary = self._summarize_projects(analysis_results)

        lines = [
            f"Projects analyzed: {project_total}",
            f"Analyzers completed: {analyzers_run}",
            f"Findings by severity: {self._format_counter(severity_counts)}",
            f"Integration levels: {self._format_counter(project_summary['integration'])}",
            f"Strategic priorities: {self._format_counter(project_summary['priority'])}",
            f"Languages: {self._format_counter(project_summary['language'])}",
            f"Recommendations generated: {len(recommendations)}",
        ]
        return "\n".join(lines)

    async def create_report(
        self,
        analysis_results: AnalysisResults,
        recommendations: List[Any],
        config: Any,
    ) -> EvaluationReport:
        if self.logger:
            self.logger.info("Report generator running")
        summary = self._build_executive_summary(analysis_results, recommendations)
        return EvaluationReport(
            analysis_results=analysis_results,
            recommendations=recommendations,
            executive_summary=summary,
        )

    async def generate_markdown(self, report: EvaluationReport) -> str:
        analysis_results = report.analysis_results
        severity_counts, findings = self._summarize_findings(analysis_results)
        project_summary = self._summarize_projects(analysis_results)

        lines: List[str] = [
            "# DevLibrary Evaluation",
            "",
            f"Generated: {report.generated_at.isoformat()}",
            "",
            "## Executive Summary",
            report.executive_summary,
            "",
            "## Project Summary",
            f"- Total projects: {len(analysis_results.projects)}",
            f"- Languages: {self._format_counter(project_summary['language'])}",
            f"- Integration levels: {self._format_counter(project_summary['integration'])}",
            f"- Strategic priorities: {self._format_counter(project_summary['priority'])}",
            "",
            "## Analyzer Results",
        ]

        for result in self._collect_analyzer_results(analysis_results):
            if not result:
                continue
            lines.extend(
                [
                    f"### {result.analyzer_name.replace('_', ' ').title()}",
                    f"- Projects analyzed: {result.projects_analyzed}",
                    f"- Duration: {result.analysis_duration:.2f}s",
                    f"- Findings: {len(result.findings)}",
                    f"- Summary: {result.summary}",
                    "",
                ]
            )

        lines.extend(
            [
                "## Findings",
                f"- Severity totals: {self._format_counter(severity_counts)}",
            ]
        )

        if findings:
            lines.append("")
            lines.append("| Severity | Title | Description |")
            lines.append("|---|---|---|")
            for finding in findings[:20]:
                severity = (finding.get("severity") or "info").lower()
                title = finding.get("title", "Untitled")
                description = finding.get("description", "")
                lines.append(f"| {severity} | {title} | {description} |")
        else:
            lines.append("- No findings reported.")

        lines.extend(
            [
                "",
                f"## Recommendations ({len(report.recommendations)} total)",
            ]
        )

        if report.recommendations:
            for rec in report.recommendations[:20]:
                lines.extend(
                    [
                        f"- **{rec.title}** ({rec.priority}, {rec.effort})",
                        f"  - Category: {rec.category}",
                        f"  - Roadmap phase: {rec.roadmap_phase}",
                        f"  - Description: {rec.description}",
                    ]
                )
        else:
            lines.append("- No recommendations generated.")

        lines.append("")
        return "\n".join(lines)

    async def generate_html(self, report: EvaluationReport) -> str:
        analysis_results = report.analysis_results
        severity_counts, findings = self._summarize_findings(analysis_results)
        project_summary = self._summarize_projects(analysis_results)

        html = [
            "<h1>DevLibrary Evaluation</h1>",
            f"<p><strong>Generated:</strong> {report.generated_at.isoformat()}</p>",
            "<h2>Executive Summary</h2>",
            "<pre>",
            report.executive_summary,
            "</pre>",
            "<h2>Project Summary</h2>",
            f"<p>Total projects: {len(analysis_results.projects)}</p>",
            f"<p>Languages: {self._format_counter(project_summary['language'])}</p>",
            f"<p>Integration levels: {self._format_counter(project_summary['integration'])}</p>",
            f"<p>Strategic priorities: {self._format_counter(project_summary['priority'])}</p>",
            "<h2>Analyzer Results</h2>",
        ]

        for result in self._collect_analyzer_results(analysis_results):
            if not result:
                continue
            html.extend(
                [
                    f"<h3>{result.analyzer_name.replace('_', ' ').title()}</h3>",
                    f"<p>Projects analyzed: {result.projects_analyzed}</p>",
                    f"<p>Duration: {result.analysis_duration:.2f}s</p>",
                    f"<p>Findings: {len(result.findings)}</p>",
                    f"<p>Summary: {result.summary}</p>",
                ]
            )

        html.extend(
            [
                "<h2>Findings</h2>",
                f"<p>Severity totals: {self._format_counter(severity_counts)}</p>",
            ]
        )
        if findings:
            html.append(
                "<table><thead><tr><th>Severity</th><th>Title</th><th>Description</th></tr></thead><tbody>"
            )
            for finding in findings[:20]:
                severity = (finding.get("severity") or "info").lower()
                title = finding.get("title", "Untitled")
                description = finding.get("description", "")
                html.append(
                    f"<tr><td>{severity}</td><td>{title}</td><td>{description}</td></tr>"
                )
            html.append("</tbody></table>")
        else:
            html.append("<p>No findings reported.</p>")

        html.append(f"<h2>Recommendations ({len(report.recommendations)} total)</h2>")
        if report.recommendations:
            html.append("<ul>")
            for rec in report.recommendations[:20]:
                html.append(
                    "<li>"
                    f"<strong>{rec.title}</strong> ({rec.priority}, {rec.effort})"
                    f"<br>Category: {rec.category}"
                    f"<br>Roadmap phase: {rec.roadmap_phase}"
                    f"<br>Description: {rec.description}"
                    "</li>"
                )
            html.append("</ul>")
        else:
            html.append("<p>No recommendations generated.</p>")

        return "\n".join(html)
