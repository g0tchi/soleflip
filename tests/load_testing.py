"""
Load Testing Script for SoleFlipper API
Tests performance and validates monitoring systems under load
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field
from statistics import mean, median, stdev
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LoadTestRequest:
    """Configuration for a load test request"""

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    json: Dict[str, Any] = None
    expected_status: int = 200


@dataclass
class LoadTestResult:
    """Result of a single request during load testing"""

    url: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LoadTester:
    """Load testing utility for API endpoints"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.results: List[LoadTestResult] = []

    async def run_load_test(
        self,
        requests: List[LoadTestRequest],
        concurrent_users: int = 10,
        duration_seconds: int = 60,
        ramp_up_seconds: int = 10,
    ) -> Dict[str, Any]:
        """
        Run load test with specified parameters

        Args:
            requests: List of request configurations to test
            concurrent_users: Number of concurrent virtual users
            duration_seconds: How long to run the test
            ramp_up_seconds: Time to gradually increase load
        """
        logger.info(
            "Starting load test",
            concurrent_users=concurrent_users,
            duration_seconds=duration_seconds,
            ramp_up_seconds=ramp_up_seconds,
        )

        self.results = []
        start_time = time.time()

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_users)

        # Start worker tasks
        tasks = []
        for i in range(concurrent_users):
            # Stagger the start time for ramp-up
            delay = (i / concurrent_users) * ramp_up_seconds
            task = asyncio.create_task(self._worker(requests, duration_seconds, delay, semaphore))
            tasks.append(task)

        # Wait for all workers to complete
        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Generate results
        return self._generate_report(total_time)

    async def _worker(
        self,
        requests: List[LoadTestRequest],
        duration_seconds: int,
        start_delay: float,
        semaphore: asyncio.Semaphore,
    ):
        """Worker coroutine that makes requests for a specified duration"""
        await asyncio.sleep(start_delay)

        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds
            request_index = 0

            while time.time() < end_time:
                async with semaphore:
                    request = requests[request_index % len(requests)]
                    result = await self._make_request(session, request)
                    self.results.append(result)
                    request_index += 1

                # Small delay to prevent overwhelming the server
                await asyncio.sleep(0.01)

    async def _make_request(
        self, session: aiohttp.ClientSession, request: LoadTestRequest
    ) -> LoadTestResult:
        """Make a single HTTP request and record results"""
        url = f"{self.base_url}{request.url}"
        start_time = time.time()

        try:
            async with session.request(
                method=request.method,
                url=url,
                headers=request.headers,
                json=request.json,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                success = response.status == request.expected_status

                return LoadTestResult(
                    url=request.url,
                    method=request.method,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    success=success,
                    error=(
                        None
                        if success
                        else f"Expected {request.expected_status}, got {response.status}"
                    ),
                )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return LoadTestResult(
                url=request.url,
                method=request.method,
                status_code=0,
                response_time_ms=response_time_ms,
                success=False,
                error=str(e),
            )

    def _generate_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive load test report"""
        if not self.results:
            return {"error": "No results to analyze"}

        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        response_times = [r.response_time_ms for r in successful_results]

        # Calculate statistics
        stats = {
            "total_requests": len(self.results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
            "requests_per_second": len(self.results) / total_time,
            "total_duration_seconds": total_time,
        }

        # Response time statistics
        if response_times:
            stats["response_times"] = {
                "mean_ms": round(mean(response_times), 2),
                "median_ms": round(median(response_times), 2),
                "min_ms": round(min(response_times), 2),
                "max_ms": round(max(response_times), 2),
                "std_dev_ms": round(stdev(response_times) if len(response_times) > 1 else 0, 2),
                "p95_ms": round(self._percentile(response_times, 95), 2),
                "p99_ms": round(self._percentile(response_times, 99), 2),
            }

        # Error analysis
        if failed_results:
            error_breakdown = {}
            for result in failed_results:
                error_key = f"{result.status_code}: {result.error}"
                error_breakdown[error_key] = error_breakdown.get(error_key, 0) + 1
            stats["error_breakdown"] = error_breakdown

        # Endpoint analysis
        endpoint_stats = {}
        for result in self.results:
            key = f"{result.method} {result.url}"
            if key not in endpoint_stats:
                endpoint_stats[key] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "response_times": [],
                }

            endpoint_stats[key]["total_requests"] += 1
            if result.success:
                endpoint_stats[key]["successful_requests"] += 1
                endpoint_stats[key]["response_times"].append(result.response_time_ms)

        # Calculate per-endpoint stats
        for endpoint, data in endpoint_stats.items():
            if data["response_times"]:
                data["avg_response_time_ms"] = round(mean(data["response_times"]), 2)
                data["success_rate"] = round(
                    data["successful_requests"] / data["total_requests"] * 100, 2
                )
            del data["response_times"]  # Remove raw data for cleaner output

        stats["endpoint_performance"] = endpoint_stats

        return stats

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c


async def run_basic_load_test():
    """Run a basic load test on key API endpoints"""

    # Define test requests
    test_requests = [
        LoadTestRequest("GET", "/health", expected_status=200),
        LoadTestRequest("GET", "/metrics", expected_status=200),
        LoadTestRequest("GET", "/metrics/apm", expected_status=200),
        LoadTestRequest("GET", "/alerts", expected_status=200),
        LoadTestRequest("GET", "/", expected_status=200),
        LoadTestRequest("GET", "/health/ready", expected_status=200),
        LoadTestRequest("GET", "/health/live", expected_status=200),
    ]

    # Create load tester
    load_tester = LoadTester()

    logger.info("Starting basic load test on monitoring endpoints")

    # Run test with moderate load
    results = await load_tester.run_load_test(
        requests=test_requests, concurrent_users=5, duration_seconds=30, ramp_up_seconds=5
    )

    logger.info("Load test completed", results=results)
    return results


async def run_stress_test():
    """Run a more intensive stress test"""

    test_requests = [
        LoadTestRequest("GET", "/health", expected_status=200),
        LoadTestRequest("GET", "/metrics", expected_status=200),
        LoadTestRequest("GET", "/alerts", expected_status=200),
    ]

    load_tester = LoadTester()

    logger.info("Starting stress test")

    # Run test with higher load
    results = await load_tester.run_load_test(
        requests=test_requests, concurrent_users=20, duration_seconds=60, ramp_up_seconds=10
    )

    logger.info("Stress test completed", results=results)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load test SoleFlipper API")
    parser.add_argument(
        "--test-type", choices=["basic", "stress"], default="basic", help="Type of load test to run"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL of the API to test"
    )

    args = parser.parse_args()

    # Setup logging
    import logging

    logging.basicConfig(level=logging.INFO)

    async def main():
        if args.test_type == "basic":
            results = await run_basic_load_test()
        else:
            results = await run_stress_test()

        # Print summary
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total Requests: {results['total_requests']}")
        print(f"Success Rate: {results['success_rate']:.2f}%")
        print(f"Requests/Second: {results['requests_per_second']:.2f}")

        if "response_times" in results:
            rt = results["response_times"]
            print(f"Average Response Time: {rt['mean_ms']:.2f}ms")
            print(f"95th Percentile: {rt['p95_ms']:.2f}ms")
            print(f"99th Percentile: {rt['p99_ms']:.2f}ms")

        if results["failed_requests"] > 0:
            print(f"\nErrors: {results['failed_requests']}")
            if "error_breakdown" in results:
                for error, count in results["error_breakdown"].items():
                    print(f"  {error}: {count}")

        print("\nEndpoint Performance:")
        for endpoint, stats in results["endpoint_performance"].items():
            print(
                f"  {endpoint}: {stats['avg_response_time_ms']:.2f}ms avg, {stats['success_rate']:.1f}% success"
            )

    asyncio.run(main())
