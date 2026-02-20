from pathlib import Path

from .counter import CounterFile
from .models import CounterResponse

mm_counter = CounterFile(Path("/var/www/mountain_madness/2026/counter.json"), save_interval=300, save_threshold=10)
mm_counter.increment("good", 0)
mm_counter.increment("evil", 0)
