import { backendUrl } from "../../types/services";
import {
  Metric,
  MetricMetadata,
  MetricValueState,
  MetricValueStateOrder
} from "../../types/metrics";
import { useDataTransformation } from "../../services/transformationService";

const metricsMetadata: Record<Metric, MetricMetadata> = {
  access: {
    fetchType: "read",
    transformationService: useDataTransformation("access"),
    base: "chunks_data",
    endpoint: backendUrl + "chunks_data"
  },
  cpu: {
    fetchType: "modify",
    transformationService: useDataTransformation("cpu"),
    base: "system_data",
    endpoint: backendUrl + "system_data"
  },
  latency: {
    fetchType: "modify",
    transformationService: useDataTransformation("latency"),
    base: "latency",
    endpoint: backendUrl + "latency"
  },
  queueLength: {
    fetchType: "modify",
    transformationService: useDataTransformation("queueLength"),
    base: "queue_length",
    endpoint: backendUrl + "queue_length"
  },
  ram: {
    fetchType: "modify",
    transformationService: useDataTransformation("ram"),
    base: "system_data",
    endpoint: backendUrl + "system_data"
  },
  storage: {
    fetchType: "read",
    transformationService: useDataTransformation("storage"),
    base: "storage",
    endpoint: backendUrl + "storage"
  },
  throughput: {
    fetchType: "modify",
    transformationService: useDataTransformation("throughput"),
    base: "throughput",
    endpoint: backendUrl + "throughput"
  }
};

const metricDetailColor: Record<MetricValueState, string> = {
  average: "#fb8c00",
  high: "#4caf50",
  low: "#ff5252"
};

const metricValueStateOrder: Record<
  MetricValueStateOrder,
  MetricValueState[]
> = {
  asc: ["low", "average", "high"],
  desc: ["high", "average", "low"]
};

const metricTitels: Record<Metric, string> = {
  access: "Access Frequency",
  cpu: "CPU",
  latency: "Latency",
  queueLength: "Queue Length",
  ram: "RAM",
  storage: "Storage",
  throughput: "Throughput"
};

const metricComponents: Record<Metric, string> = {
  access: "Access",
  cpu: "CPU",
  latency: "Latency",
  queueLength: "QueueLength",
  ram: "RAM",
  storage: "Storage",
  throughput: "Throughput"
};

export function getMetricComponent(metric: Metric): string {
  return metricComponents[metric];
}
export function getMetricTitle(metric: Metric): string {
  return metricTitels[metric];
}

export function getMetricValueStateOrder(
  order: MetricValueStateOrder
): MetricValueState[] {
  return metricValueStateOrder[order];
}

export function getMetricDetailColor(value: MetricValueState): string {
  return metricDetailColor[value];
}

export function getMetadata(metric: Metric): MetricMetadata {
  return metricsMetadata[metric];
}
