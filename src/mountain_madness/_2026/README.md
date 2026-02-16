# A counter created for Mountain Madness 2026

* The file it writes to is `/var/www/mountain_madness/2026/counter.json`
* It contains the four following endpoints (root is `/api/mm2026`)
    * GET `/counters`: Returns the counter values
    * POST `/good`: Increments the Good counter
    * POST `/evil`: Increments the Evil counter
