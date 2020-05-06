import { getSelectorByConfig, clickElement } from "../helpers";

const routes: Record<string, string> = {
  home: "/#/",
  overview: "/#/databases/overview",
  comparison: "/#/databases/compare",
  workloadMonitoring: "/#/workload",
};

const selectors: Record<string, string> = {
  overviewButton: getSelectorByConfig("a", "overview-button"),
  comparisonButton: getSelectorByConfig("a", "comparison-button"),
  workloadMonitoringButton: getSelectorByConfig(
    "a",
    "workload-monitoring-button"
  ),
  databaseListButton: getSelectorByConfig("div", "database-list-button"),
  workloadGenerationButton: getSelectorByConfig(
    "div",
    "workload-generation-button"
  ),
  pluginOverviewButton: getSelectorByConfig("div", "plugin-overview-button"),
  selectionListButton: getSelectorByConfig("button", "selection-list-button"),
  pluginOverview: getSelectorByConfig("div", "plugin-overview"),
  databaseList: getSelectorByConfig("div", "database-list"),
  workloadGeneration: getSelectorByConfig("div", "workload-generation"),
  selectionList: getSelectorByConfig("div", "selection-list"),
  unselectDatabase: getSelectorByConfig("button", "add-select-database-button"),
  selectDatabase: getSelectorByConfig(
    "button",
    "remove-select-database-button"
  ),
  unselectMetric: getSelectorByConfig("button", "add-select-metric-button"),
  selectMetric: getSelectorByConfig("button", "remove-select-metric-button"),
  overviewPage: getSelectorByConfig("div", "overview-page"),
  comparisonPage: getSelectorByConfig("div", "comparison-page"),
  workloadMonitoringPage: getSelectorByConfig(
    "div",
    "workload-monitoring-page"
  ),
  metricChip: getSelectorByConfig("span", "metric-chip"),
  loadingAnimation: getSelectorByConfig("div", "loading-animation"),
  historicRangeSelection: getSelectorByConfig(
    "input",
    "historic-range-selection"
  ),
  precisionSelection: getSelectorByConfig("input", "precision-selection"),
};

const metrics: Record<string, string[]> = {
  workloadMonitoring: ["generatedQueryTypeProportion"],
  comparison: [
    "throughput",
    "latency",
    "queueLength",
    "cpu",
    "ram",
    "memoryFootprint",
    "storage",
    "access",
    "executedQueryTypeProportion",
  ],
  overview: [
    "throughput",
    "latency",
    "queueLength",
    "cpu",
    "ram",
    "memoryFootprint",
  ],
};

export function getSelector(component: string): string {
  return selectors[component];
}

export function getRoute(component: string): string {
  return routes[component];
}

export function getMetrics(component: string): string[] {
  return metrics[component];
}

export function testRedirection(selector: string, newRoute: string): void {
  clickElement(selector);
  cy.url().should("contain", newRoute);
}

export function checkMultipleMetrics(metric: string): string {
  if (metric === "storage") return "secondStorage";
  if (metric === "access") return "secondAccess";
  return metric;
}

export function assertItemSelect(
  component: "database" | "metric",
  selected: boolean
): void {
  if (component === "database" && selected) {
    cy.get(getSelector("selectDatabase")).should("not.be.visible", {
      force: true,
    });
    cy.get(getSelector("unselectDatabase"))
      .scrollIntoView()
      .should("be.visible", {
        force: true,
      });
  } else if (component === "database" && !selected) {
    cy.get(getSelector("selectDatabase"))
      .scrollIntoView()
      .should("be.visible", { force: true });
    cy.get(getSelector("unselectDatabase")).should("not.be.visible", {
      force: true,
    });
  } else if (component === "metric" && selected) {
    cy.get(getSelector("selectMetric")).should("not.be.visible", {
      force: true,
    });
    cy.get(getSelector("unselectMetric"))
      .scrollIntoView()
      .should("be.visible", { force: true });
  } else if (component === "metric" && !selected) {
    cy.get(getSelector("selectMetric"))
      .scrollIntoView()
      .should("be.visible", { force: true });
    cy.get(getSelector("unselectMetric")).should("not.be.visible", {
      force: true,
    });
  }
}
