"""Container launcher: run harness.bench with only the frozen bench deps on sys.path."""

import sys
from pathlib import Path

sys.path[:0] = ["/opt/bench/site", str(Path(__file__).resolve().parent.parent)]

from harness.bench import main  # noqa: E402

main(sys.argv[1])
