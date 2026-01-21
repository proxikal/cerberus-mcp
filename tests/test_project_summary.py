from pathlib import Path

from cerberus.analysis.project_summary import ProjectSummaryAnalyzer


def test_go_project_detection(tmp_path: Path) -> None:
    go_mod = tmp_path / "go.mod"
    go_mod.write_text(
        "\n".join(
            [
                "module example.com/foo",
                "go 1.23",
                "",
                "require (",
                "    github.com/go-chi/chi/v5 v5.0.0",
                "    github.com/a-h/templ v0.1.0",
                "    github.com/jackc/pgx/v5 v5.5.0",
                ")",
            ]
        )
    )
    main_go = tmp_path / "core" / "cmd" / "web" / "main.go"
    main_go.parent.mkdir(parents=True, exist_ok=True)
    main_go.write_text("package main\n\nfunc main() {}\n")

    analyzer = ProjectSummaryAnalyzer(tmp_path)
    summary = analyzer.generate_summary()

    assert summary.project_type == "Go Web Application"
    assert "Go 1.23" in summary.tech_stack
    assert "Chi (HTTP router)" in summary.tech_stack
    assert "Templ (Templating)" in summary.tech_stack
    assert "PostgreSQL" in summary.tech_stack
    assert "core/cmd/web/main.go" in summary.entry_points


def test_js_project_detection(tmp_path: Path) -> None:
    package_json = tmp_path / "package.json"
    package_json.write_text(
        """
{
  "dependencies": {
    "express": "latest",
    "react": "latest",
    "typescript": "5.3.3"
  }
}
        """.strip()
    )
    entry = tmp_path / "index.ts"
    entry.write_text("export const main = () => {};\n")

    analyzer = ProjectSummaryAnalyzer(tmp_path)
    summary = analyzer.generate_summary()

    assert summary.project_type == "Express.js Application"
    assert "Express.js" in summary.tech_stack
    assert "React" in summary.tech_stack
    assert "TypeScript" in summary.tech_stack
    assert "index.ts" in summary.entry_points


def test_python_project_regression(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["fastapi"]
requires-python = "3.11"
        """.strip()
    )
    main_py = tmp_path / "app.py"
    main_py.write_text("def create_app():\n    return None\n")

    analyzer = ProjectSummaryAnalyzer(tmp_path)
    summary = analyzer.generate_summary()

    assert summary.project_type == "FastAPI Application"
    assert "Python 3.11" in summary.tech_stack
    assert "FastAPI" in summary.tech_stack
    assert "app.py" in summary.entry_points
