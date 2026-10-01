"""Background jobs (ADR-009, BACKEND.md §4). `framework` holds the retry and session wrapper,
`queue` the enqueue helper the API and jobs use, and the other modules the job functions the
worker (`app/worker.py`) registers."""
