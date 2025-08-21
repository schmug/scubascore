"""Report generation for SCuBA Scoring Kit."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import html

from .models import ScoreResult, ServiceScore, Rule
from .exceptions import ReportingError

logger = logging.getLogger(__name__)


def generate_reports(
    result: ScoreResult,
    output_prefix: Union[str, Path],
    formats: Optional[List[str]] = None,
) -> Dict[str, Path]:
    """Generate reports in multiple formats.
    
    Args:
        result: ScoreResult object
        output_prefix: Prefix for output filenames
        formats: List of output formats (default: ["json", "csv", "html"])
        
    Returns:
        Dictionary mapping format names to output paths
        
    Raises:
        ReportingError: If report generation fails
    """
    if formats is None:
        formats = ["json", "csv", "html"]
    
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    for fmt in formats:
        try:
            if fmt == "json":
                outputs["json"] = write_json_report(result, output_prefix)
            elif fmt == "csv":
                outputs["csv"] = write_csv_report(result, output_prefix)
            elif fmt == "html":
                outputs["html"] = write_html_report(result, output_prefix)
            else:
                logger.warning(f"Unknown output format: {fmt}")
        except Exception as e:
            logger.error(f"Failed to generate {fmt} report: {e}")
            raise ReportingError(f"Failed to generate {fmt} report: {e}") from e
    
    return outputs


def write_json_report(result: ScoreResult, prefix: Path) -> Path:
    """Write detailed JSON report.
    
    Args:
        result: ScoreResult object
        prefix: Output file prefix
        
    Returns:
        Path to generated JSON file
    """
    output_path = Path(f"{prefix}_scores.json")
    
    # Convert to dictionary with additional details
    data = result.to_dict()
    
    # Add failed rules details (now handled by to_dict method)
    # No need for additional processing as to_dict includes all details
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Generated JSON report: {output_path}")
    return output_path


def write_csv_report(result: ScoreResult, prefix: Path) -> Path:
    """Write CSV report with service scores.
    
    Args:
        result: ScoreResult object
        prefix: Output file prefix
        
    Returns:
        Path to generated CSV file
    """
    output_path = Path(f"{prefix}_analysis.csv")
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Write summary section
        writer.writerow([
            "Service",
            "Score (%)",
            "Status",
            "Evaluated Weight",
            "Passed Weight",
            "Passed Rules",
            "Failed Rules",
            "Rules with Compensating Controls",
        ])
        
        # Write service data
        for service_name in sorted(result.service_scores.keys()):
            service = result.service_scores[service_name]
            
            # Determine status
            status = "N/A"
            if service.score is not None:
                if service.score >= 90:
                    status = "Excellent"
                elif service.score >= 80:
                    status = "Good"
                elif service.score >= 70:
                    status = "Fair"
                elif service.score >= 60:
                    status = "Poor"
                else:
                    status = "Critical"
            
            # Count compensating controls
            comp_controls = sum(
                1 for rule in service.failed_rules if rule.compensating_control
            )
            
            writer.writerow([
                service_name,
                service.score if service.score is not None else "",
                status,
                service.evaluated_weight,
                service.passed_weight,
                service.passed_count,
                service.failed_count,
                comp_controls,
            ])
        
        # Write summary rows
        writer.writerow([])
        writer.writerow(["Overall Score", result.overall_score or "N/A"])
        writer.writerow(["Generated At", result.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")])
        
        # Write detailed failed rules section
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Failed Rules Detail"])
        writer.writerow([
            "Service",
            "Rule ID",
            "Requirement",
            "Weight",
            "Compensating Control",
            "Documentation URL"
        ])
        
        for service_name in sorted(result.service_scores.keys()):
            service = result.service_scores[service_name]
            for rule in service.failed_rules:
                writer.writerow([
                    service_name,
                    rule.rule_id,
                    rule.requirement or "",
                    rule.weight,
                    "Yes" if rule.compensating_control else "No",
                    rule.documentation_url or ""
                ])
    
    logger.info(f"Generated CSV report: {output_path}")
    return output_path


def write_html_report(result: ScoreResult, prefix: Path) -> Path:
    """Write executive HTML report.
    
    Args:
        result: ScoreResult object
        prefix: Output file prefix
        
    Returns:
        Path to generated HTML file
    """
    output_path = Path(f"{prefix}_report.html")
    
    # Generate service rows
    service_rows = []
    for service_name in sorted(result.service_scores.keys()):
        service = result.service_scores[service_name]
        
        # Determine color based on score
        color_class = ""
        if service.score is not None:
            if service.score >= 90:
                color_class = "excellent"
            elif service.score >= 80:
                color_class = "good"
            elif service.score >= 70:
                color_class = "fair"
            elif service.score >= 60:
                color_class = "poor"
            else:
                color_class = "critical"
        
        # Count compensating controls
        comp_controls = sum(
            1 for rule in service.failed_rules if rule.compensating_control
        )
        
        service_rows.append(
            f'<tr class="{color_class}">'
            f'<td>{html.escape(service_name)}</td>'
            f'<td class="score">{service.score if service.score is not None else "N/A"}</td>'
            f'<td>{service.evaluated_weight}</td>'
            f'<td>{service.passed_weight}</td>'
            f'<td>{service.passed_count}</td>'
            f'<td>{service.failed_count}</td>'
            f'<td>{comp_controls}</td>'
            '</tr>'
        )
    
    # Generate failed rules section
    failed_rules_html = ""
    for service_name, service in result.service_scores.items():
        if service.failed_rules:
            failed_rules_html += f'<h4>{html.escape(service_name)}</h4>\n<ul class="failed-rules">\n'
            for rule in service.failed_rules:
                comp_text = " (compensating control applied)" if rule.compensating_control else ""
                
                # Create the rule item with optional link
                if rule.documentation_url:
                    rule_html = f'<a href="{html.escape(rule.documentation_url)}" target="_blank" rel="noopener">{html.escape(rule.rule_id)}</a>'
                else:
                    rule_html = html.escape(rule.rule_id)
                
                # Add requirement tooltip if available
                if rule.requirement:
                    # Clean up requirement text (remove HTML entities)
                    req_text = rule.requirement.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
                    rule_html += f' <span class="requirement" title="{html.escape(req_text)}">ⓘ</span>'
                
                failed_rules_html += f'<li>{rule_html} <span class="weight">(weight: {rule.weight})</span>{comp_text}</li>\n'
            failed_rules_html += '</ul>\n'
    
    # Generate overall score color
    overall_color = ""
    if result.overall_score is not None:
        if result.overall_score >= 90:
            overall_color = "excellent"
        elif result.overall_score >= 80:
            overall_color = "good"
        elif result.overall_score >= 70:
            overall_color = "fair"
        elif result.overall_score >= 60:
            overall_color = "poor"
        else:
            overall_color = "critical"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SCuBA Security Score Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .overall-score {{
            background-color: #f8f9fa;
            padding: 40px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .score-display {{
            font-size: 4rem;
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .score-label {{
            font-size: 1.2rem;
            color: #6c757d;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: #495057;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        
        .section h3 {{
            font-size: 1.4rem;
            margin-bottom: 15px;
            color: #6c757d;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        
        tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .score {{
            font-weight: bold;
        }}
        
        .excellent {{ color: #28a745; }}
        .good {{ color: #17a2b8; }}
        .fair {{ color: #ffc107; }}
        .poor {{ color: #fd7e14; }}
        .critical {{ color: #dc3545; }}
        
        .data-quality {{
            background-color: #e9ecef;
            padding: 20px;
            border-radius: 4px;
            margin-top: 20px;
        }}
        
        .data-quality h4 {{
            margin-bottom: 10px;
            color: #495057;
        }}
        
        .metadata {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9rem;
            border-top: 1px solid #e9ecef;
        }}
        
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        
        ul li {{
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
        }}
        
        ul li:before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #dc3545;
            font-weight: bold;
        }}
        
        .failed-rules a {{
            color: #0066cc;
            text-decoration: none;
        }}
        
        .failed-rules a:hover {{
            text-decoration: underline;
        }}
        
        .requirement {{
            cursor: help;
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        .weight {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}
            
            .score-display {{
                font-size: 3rem;
            }}
            
            table {{
                font-size: 0.9rem;
            }}
            
            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SCuBA Security Score Report</h1>
            <div class="subtitle">Google Workspace Security Configuration Assessment</div>
        </div>
        
        <div class="overall-score">
            <div class="score-label">Overall Security Score</div>
            <div class="score-display {overall_color}">
                {result.overall_score if result.overall_score is not None else "N/A"}%
            </div>
            <div class="score-label">Generated on {result.generated_at.strftime("%B %d, %Y at %H:%M UTC")}</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Service Scores</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Service</th>
                            <th>Score</th>
                            <th>Evaluated Weight</th>
                            <th>Passed Weight</th>
                            <th>Passed Rules</th>
                            <th>Failed Rules</th>
                            <th>Compensating Controls</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(service_rows)}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>Failed Rules by Service</h2>
                {failed_rules_html if failed_rules_html else "<p>No failed rules to report.</p>"}
            </div>
            
            <div class="data-quality">
                <h4>Data Quality Metrics</h4>
                <p>Total entries processed: {result.data_quality.total_entries}</p>
                <p>Entries skipped (unknown/error): {result.data_quality.unknown_or_error_entries}</p>
                <p>Not applicable entries: {result.data_quality.na_entries}</p>
            </div>
        </div>
        
        <div class="metadata">
            Generated by SCuBA Scoring Kit v1.0.0 | 
            Report ID: {result.generated_at.strftime("%Y%m%d-%H%M%S")}
        </div>
    </div>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"Generated HTML report: {output_path}")
    return output_path


def write_markdown_report(result: ScoreResult, prefix: Path) -> Path:
    """Write Markdown report.
    
    Args:
        result: ScoreResult object
        prefix: Output file prefix
        
    Returns:
        Path to generated Markdown file
    """
    output_path = Path(f"{prefix}_report.md")
    
    lines = [
        "# SCuBA Security Score Report",
        "",
        f"**Generated:** {result.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Overall Score",
        "",
        f"**{result.overall_score}%** " if result.overall_score is not None else "**N/A**",
        "",
        "## Service Scores",
        "",
        "| Service | Score | Passed | Failed | Compensating Controls |",
        "|---------|-------|--------|--------|--------------------|",
    ]
    
    for service_name in sorted(result.service_scores.keys()):
        service = result.service_scores[service_name]
        comp_controls = sum(1 for _, _, has_comp in service.failed_rules if has_comp)
        
        score_str = f"{service.score}%" if service.score is not None else "N/A"
        lines.append(
            f"| {service_name} | {score_str} | {service.passed_count} | "
            f"{service.failed_count} | {comp_controls} |"
        )
    
    lines.extend([
        "",
        "## Failed Rules",
        "",
    ])
    
    for service_name, service in sorted(result.service_scores.items()):
        if service.failed_rules:
            lines.append(f"### {service_name}")
            lines.append("")
            for rule_id, weight, has_comp in service.failed_rules:
                comp_text = " *(compensating control applied)*" if has_comp else ""
                lines.append(f"- {rule_id} (weight: {weight}){comp_text}")
            lines.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    logger.info(f"Generated Markdown report: {output_path}")
    return output_path