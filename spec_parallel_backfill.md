# Specification: Optimized Parallel Backfill & Resource Management
(최적화된 병렬 백필 및 리소스 관리 명세서)

## 1. Feasibility Study (타당성 검토)
- **Technical Feasibility**: High. The existing `AddressCollector` logic already supports both collection directions. The core change is in job orchestration (Splitting 1 job into 2 MQ tasks) and UI aggregation.
- **Performance Impact**: Expected 2x speedup for single-stock backfills. No impact on system stability if `prefetch_count=1` is strictly enforced.
- **Risk Assessment**: Potential for DB lock contention if two workers update the same job record simultaneously. Mitigation: Use atomic progress increments or task-specific columns.

## 2. Requirement Specification (요구사항 명세)

### 2.1 Functional Requirements (기능 요구사항)
- **[R-01] Unified Backfill Identity**: A backfill request for a stock must be treated as a SINGLE job in the database and UI.
- **[R-02] Bi-Directional Segmentation**: A backfill job for $N$ days must be split into:
  - **Segment A (Recent)**: Today backward to $N/2$ days. (Direction: Backward)
  - **Segment B (Historical)**: Past limit ($N$ days ago) forward to $N/2$ days. (Direction: Forward)
- **[R-03] Task Parallelism**: Segment A and Segment B must be deliverable to separate workers concurrently.
- **[R-04] Strict Resource Occupancy**: If the backfill worker pool ($W=2$) is fully occupied by Stock A's segments, Stock B's segments must remain in the queue (PENDING).
- **[R-05] Isolated Daily Priority**: The `daily_address_worker` thread must remain isolated on its own queue to ensure real-time news collection is never blocked by backfill data.

### 2.2 Domain Logic & Conflict Review (도메인 로직 및 충돌 검토)
- **Contradiction Check**: Creating two MQ tasks for one Job ID.
  - *Conflict*: If we simply reuse the `job_id`, how do we know when the *entire* job is done?
  - *Resolution*: Tasks must be identified as `Sub-Task A` and `Sub-Task B`. A completion check must run when a sub-task finishes to see if the sibling is also done.
- **Redundancy Check**: 
  - *Observation*: Current `is_incremental` logic is redundant with the new `direction` parameter.
  - *Resolution*: Deprecate automatic inference based on `backfill_completed_at` in favor of explicit `direction` parameters from the dispatcher.

---

## 3. Revised Implementation Workflow (개정된 구현 워크플로우)

### Phase 1: Database Schema Expansion
- Update `jobs` table to handle multi-task progress. 
- (Option: Add `parent_job_id` or just track `segment_1_done` and `segment_2_done` flags in the params).

### Phase 2: Orchestration Refactor
- `JobManager.create_backfill_job` creates ONE job record.
- Publishes TWO messages to `address_jobs`. Each message contains `job_id` and its specific `segment` instructions.

### Phase 3: Worker Adaptation
- `AddressCollector` processes the segment and updates progress.
- Upon completion, it marks its segment as done in the DB and checks if the other segment is also done to finalize the Job.

### Phase 4: UI/UX Calibration
- The Dashboard UI will only show one row per backfill, with an aggregate progress bar.
- Status will correctly reflect 'PENDING' until at least one worker picks up a segment.
