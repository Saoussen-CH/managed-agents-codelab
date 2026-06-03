from __future__ import annotations
from pathlib import Path
from backend.models import AppConfig, RunRecord

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class Storage:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.runs_dir = data_dir / "runs"
        self.config_path = data_dir / "config.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def read_config(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        return AppConfig.model_validate_json(self.config_path.read_text())

    def write_config(self, config: AppConfig) -> None:
        self.config_path.write_text(config.model_dump_json(indent=2))

    def write_run(self, run: RunRecord) -> None:
        path = self.runs_dir / f"{run.id}.json"
        path.write_text(run.model_dump_json(indent=2))

    def read_run(self, run_id: str) -> RunRecord | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return RunRecord.model_validate_json(path.read_text())

    def list_runs(self) -> list[RunRecord]:
        runs = [
            RunRecord.model_validate_json(p.read_text())
            for p in self.runs_dir.glob("*.json")
        ]
        return sorted(runs, key=lambda r: r.started_at, reverse=True)


storage = Storage()
