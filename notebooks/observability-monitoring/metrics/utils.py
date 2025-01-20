"""Utility functions for Metrics Notebook"""

import random
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    Optional,
)

import boto3
import matplotlib.pyplot as plt
import pandas as pd

# from rich import print

try:
    from mypy_boto3_cloudwatch import CloudWatchClient
    from mypy_boto3_cloudwatch.type_defs import ListMetricsOutputTypeDef
except ImportError:
    pass


def plot_line_graph(metrics_data_agg: pd.DataFrame) -> None:
    """
    Plot a line graph for the aggregated metrics data.

    Args:
        metrics_data_agg (pd.DataFrame): Aggregated metrics DataFrame with Timestamp, Label, and metrics columns.
    """
    # Pivot the data to prepare for plotting
    pivot_df = metrics_data_agg.pivot(index="Timestamp", columns="Label", values="P95")

    # Plot the data
    plt.figure(figsize=(15, 6))
    pivot_df.plot(ax=plt.gca(), marker="o", linestyle="-")

    plt.title("P95 ResponseLatency by Label Over Time", fontsize=16)
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("95$^{th}$ Percentile Response Time (ms)", fontsize=12)
    plt.legend(title="Label")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_stacked_area_graph(metrics_data_agg: pd.DataFrame) -> None:
    """
    Plot a stacked area graph for the aggregated metrics data.

    Args:
        metrics_data_agg (pd.DataFrame): Aggregated metrics DataFrame with Timestamp, Label, and metrics columns.
    """
    # Pivot the data to prepare for plotting
    pivot_df = metrics_data_agg.pivot(index="Timestamp", columns="Label", values="P95")

    # Plot the data
    plt.figure(figsize=(15, 6))
    pivot_df.plot(kind="area", ax=plt.gca(), alpha=0.7)

    plt.title("P95 Response Time by Label Over Time", fontsize=16)
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("95$^{th}$ Percentile Response Time (ms)", fontsize=12)
    plt.legend(title="Label")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def generate_random_metrics_df(
    namespace: str, metric_name: str, unit: str, num_points: int, hours: int, publish: bool = True
) -> pd.DataFrame:
    """
    Generate random metrics data with random timestamps & dimensions and publishs to CloudWatch.
    Returns the metrics data as a DataFrame.

    Args:
        namespace (str): The namespace for the metric data
        metric_name (str): The name of the metric
        unit (str): The unit of the metric
        num_points (int): The number of data points to generate
        hours (int): Time range in hours before the current time.
        publish (bool, optional): Whether to publish the metrics to CloudWatch. Defaults to True.

    Returns:
        pd.DataFrame: The metrics data as a DataFrame
    """
    metrics_data = []

    # Generate random timestamps within x hour
    timestamps = generate_random_timestamps(num_points, hours=hours)

    for timestamp in timestamps:
        # Generate a random value for response latency (e.g., 10ms to 2000ms)
        value = random.uniform(10, 2000)
        # Include random dimensions such as "Endpoint", "Method", and "Status"
        dimensions = get_random_dimensions()
        metric = create_metric_data(metric_name, value, unit, timestamp, dimensions)
        metrics_data.extend(metric)

    # Convert to DataFrame and sort by timestamp
    metrics_df = pd.DataFrame(metrics_data)
    metrics_df.sort_values("Timestamp", inplace=True, ignore_index=True)

    if publish:
        for _, metric in metrics_df.iterrows():
            put_metric_data(namespace, [metric.to_dict()])

        print(
            f"Successfully published {num_points} metrics to CloudWatch "
            f"over a time range of the past {hours} hour(s)."
        )

    return metrics_df


def generate_random_timestamps(n: int, hours: int) -> list[datetime]:
    """
    Generate N random timestamps within the past X hours.

    Args:
        n (int): Number of timestamps to generate.
        hours (int): Time range in hours before the current time.

    Returns:
        list[datetime]: List of random datetime objects.
    """
    now = datetime.now(timezone.utc)  # datetime.utcnow()
    start_time = now - timedelta(hours=hours)

    return [start_time + timedelta(seconds=random.uniform(0, (now - start_time).total_seconds())) for _ in range(n)]


def get_random_dimensions() -> list[dict]:
    """
    Generate random dimensions for the metric data.

    Returns:
        list[dict]: List of random dimensions.
    """
    dimensions_dict = {
        "endpoint": [
            "/api/v1/files"
        ],  # you can add more endpoints and other dimensions but that will increase the combinations of metrics that are generated
        "method": ["GET", "POST"],
        "status": ["200", "201"],
    }
    dimensions = [
        {"Name": "Endpoint", "Value": random.choice(dimensions_dict["endpoint"])},
        {"Name": "Method", "Value": random.choice(dimensions_dict["method"])},
        {"Name": "Status", "Value": random.choice(dimensions_dict["status"])},
    ]
    return dimensions


def create_metric_data(
    metric_name: str,
    value: float,
    unit: str,
    timestamp: datetime | None = None,
    dimensions: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """
    Create a single metric data point for CloudWatch. If dimensions are provided, they will be included in the metric data.
    If a timestamp is not provided, the current UTC time will be used.

    Args:
        metric_name (str): The name of the metric
        value (float): The value of the metric
        unit (str): The unit of the metric
        dimensions (list[dict]): The dimensions of the metric

        Valid Values for Unit in CloudWatch: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDatum.html

    Returns:
        list[dict]: The metric data
    """
    metric_data = {"MetricName": metric_name, "Value": value, "Unit": unit}
    if dimensions:
        metric_data["Dimensions"] = dimensions
    if timestamp:
        metric_data["Timestamp"] = timestamp

    return [metric_data]


def put_metric_data(
    namespace: str,
    metric_data: list[dict],
    cw_client: Optional["CloudWatchClient"] = None,
) -> None:
    """
    Put metric data to CloudWatch. This metric is given a timestamp of the current UTC time.

    Args:
        namespace (str): The namespace for the metric data
        metric_data (list[dict]): The metric data to put
        cw_client (CloudWatchClient, optional): The CloudWatch client to use. Defaults to None.
    Returns:
        None
    """
    cw_client = cw_client or boto3.client("cloudwatch")
    cw_client.put_metric_data(Namespace=namespace, MetricData=metric_data)


def list_metrics(namespace: str, cw_client: Optional["CloudWatchClient"] = None) -> "ListMetricsOutputTypeDef":
    """
    List metrics in CloudWatch

    Args:
        namespace (str): The namespace for the metrics
        cw_client (CloudWatchClient, optional): The CloudWatch client to use. Defaults to None.

    Returns:
        list[dict]: List the specified metrics.
    """
    cw_client = cw_client or boto3.client("cloudwatch")
    metrics: "ListMetricsOutputTypeDef" = cw_client.list_metrics(Namespace=namespace)  # ["Metrics"]
    return metrics
