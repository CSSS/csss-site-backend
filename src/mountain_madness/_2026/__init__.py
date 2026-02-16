from counter import CounterFile

from .models import CounterResponse

mm_counter = CounterFile("/var/lib/mountain_madness/2026/counter.json", save_interval=300, save_threshold=10)
