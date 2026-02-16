from .counter import CounterFile
from .models import CounterResponse

mm_counter = CounterFile("/var/www/mountain_madness/2026/counter.json", save_interval=300, save_threshold=10)
mm_counter.increment("good", 0)  # initialize the counter with default values if it doesn't exist
mm_counter.increment("evil", 0)  # initialize the counter with default values if it doesn't exist
