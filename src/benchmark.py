
import statistics
import time

from src.engine import run_engine


def main():
    runs = 3
    timings = []

    for run_number in range(1, runs + 1):
        start = time.perf_counter()
        run_engine()
        elapsed = time.perf_counter() - start

        timings.append(elapsed)
        print(f"Run {run_number}: {elapsed:.3f} seconds")

    print("\nPERFORMANCE SUMMARY")
    print(f"Runs: {runs}")
    print(f"Average: {statistics.mean(timings):.3f} seconds")
    print(f"Minimum: {min(timings):.3f} seconds")
    print(f"Maximum: {max(timings):.3f} seconds")


if __name__ == "__main__":
    main()
