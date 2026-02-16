# A counter created for Mountain Madness 2026

* The file it writes to is `/var/lib/mountain_madness/2026/counters.json`
* It contains the four following endpoints (root is `/api/mm2026`)
    * POST `/good`: Increments the Good counter
    * GET `/good`: Returns the Good count
    * POST `/evil`: Increments the Evil counter
    * GET `/evil`: Returns the Evil count
