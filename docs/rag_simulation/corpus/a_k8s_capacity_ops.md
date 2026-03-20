# A3 Kubernetes Capacity Operations Guide

## Cluster Baseline

- Cluster autoscaler min nodes: `8`.
- Cluster autoscaler max nodes: `40`.
- During release freeze, keep at least `15` schedulable nodes.

## HPA and Resource Thresholds

- HPA target CPU utilization: `60%`.
- HPA target memory utilization: `70%`.
- Node disk pressure eviction threshold: `85%`.
- Node memory pressure threshold: `90%`.

## Capacity Alerts

- Trigger capacity alert when `Pending Pods > 20` for `5 minutes`.
- Trigger image pull escalation when same image has `3` consecutive `ImagePullBackOff`.
- If API server latency `p99 > 1.2s` for `10 minutes`, pause non-critical rollout.

## On-Call Actions

1. Confirm namespace-level quota usage.
2. Check node allocatable CPU/memory trend in last 30 minutes.
3. Scale node group first, then tune workload requests/limits.
