import json
import os
import subprocess
import sys
from pathlib import Path


def test_checkpoint_survives_process_restart(tmp_path: Path) -> None:
    checkpoint_db = tmp_path / "checkpoints.sqlite"
    reservations_file = tmp_path / "reservations.json"

    env = os.environ.copy()
    env["TEST_CHECKPOINT_DB"] = str(checkpoint_db)
    env["TEST_RESERVATIONS_FILE"] = str(reservations_file)

    assert not checkpoint_db.exists()
    assert not reservations_file.exists()

    pause_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.conversational_agent.helpers.checkpoint_pause",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert pause_result.returncode == 0, f"Pause process failed:\n{pause_result.stderr}"

    assert checkpoint_db.exists()
    assert not reservations_file.exists()

    resume_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.conversational_agent.helpers.checkpoint_resume",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resume_result.returncode == 0, (
        f"Resume process failed:\n{resume_result.stderr}"
    )

    assert reservations_file.exists()

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert len(reservations) == 1
