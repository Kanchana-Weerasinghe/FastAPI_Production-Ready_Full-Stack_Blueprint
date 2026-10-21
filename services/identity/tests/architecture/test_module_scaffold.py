import subprocess
import sys
from pathlib import Path
from shutil import copyfile


def test_scaffold_creates_the_standard_module_layers(
    tmp_path: Path,
) -> None:
    """Verify generated modules match the established layers, naming and public API."""
    server_dir = tmp_path / "server"
    app_dir = server_dir / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(
        "# [scaffold:model-imports]\n\n# [scaffold:model-exports]\n",
        encoding="utf-8",
    )
    (app_dir / "container.py").write_text(
        "# [scaffold:container-imports]\n\n# [scaffold:container-providers]\n",
        encoding="utf-8",
    )
    (app_dir / "api.py").write_text(
        "# [scaffold:router-imports]\n\n# [scaffold:router-includes]\n",
        encoding="utf-8",
    )

    scripts_dir = server_dir / "scripts"
    scripts_dir.mkdir()
    source_scripts = Path(__file__).resolve().parents[2] / "scripts"
    for filename in ("new_module.py", "new_module_architecture.py"):
        copyfile(source_scripts / filename, scripts_dir / filename)
    subprocess.run(
        [sys.executable, str(scripts_dir / "new_module.py"), "projects"],
        cwd=server_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    module_dir = app_dir / "modules" / "projects"
    for layer in (
        "domain",
        "application/ports",
        "application/use_cases",
        "infrastructure/persistence",
    ):
        layer_dir = module_dir / layer
        assert layer_dir.is_dir()
        assert (layer_dir / "__init__.py").is_file()

    public_source = (module_dir / "public.py").read_text(encoding="utf-8")
    router_source = (module_dir / "router.py").read_text(encoding="utf-8")
    port_source = (module_dir / "application/ports/project_repository.py").read_text(encoding="utf-8")
    adapter_source = (module_dir / "infrastructure/persistence/sqlalchemy_project_repository.py").read_text(
        encoding="utf-8"
    )
    assert "CreateProject" in public_source
    assert "from app.modules.projects.public import CreateProject" in router_source
    assert "class ProjectRepository(ABC):" in port_source
    assert "class SqlAlchemyProjectRepository(ProjectRepository):" in adapter_source
