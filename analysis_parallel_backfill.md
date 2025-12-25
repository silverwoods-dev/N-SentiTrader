# Analysis: Parallel Backfill Mechanism (병렬 백필 메커니즘 분석)

## 1. Feasibility Study (타당성 검토)

### Current System (현황)
- `AddressCollector` handles both **Backward** (Newest -> Oldest) and **Forward** (Oldest -> Newest) collection.
- However, a single `backfill` job is assigned to only **one worker** and processes dates linearly.
- This creates a "Time-Gap" issue when extending backfill periods, as recent news is only reached after historical data is processed.

### Proposed Parallel Approach (제안된 병렬 접근 방식)
- Assign two workers to a single backfill request:
  - **Worker A (Forward-Historical)**: `Start Date -> Mid-point`. Ensures old history is filled.
  - **Worker B (Backward-Recent)**: `Current Date -> Mid-point`. Ensures the most recent news is collected first.
- **Feasibility Result**: **High**. 
  - The current `AddressCollector.handle_job` logic already contains both loops. We just need to split the `days` and `offset` parameters and launch two sub-jobs or update the worker to handle specific ranges more flexibly.

---

## 2. Requirement Analysis (요구사항 분석)

### Functional Requirements (기능 요구사항)
1. **Range Splitting**: When a backfill for $X$ days is requested, the system must split the range into $[0, X/2]$ and $[X/2, X]$.
2. **Direction Control**:
   - Sub-Job 1 (Recent): Start from `Now`, go backward to `Now - X/2`. (**Backward mode**)
   - Sub-Job 2 (Historical): Start from `Now - X`, go forward to `Now - X/2`. (**Forward mode**)
3. **Queue Prioritization**:
   - All backfill jobs remain in `JOB_QUEUE_NAME` (normal priority), while `DAILY_JOB_QUEUE_NAME` remains reserved for real-time daily updates.
4. **Worker Parallelism**: Two separate `address_worker` containers (or instances) must be able to pull these tasks simultaneously.

### Non-Functional Requirements (비기능 요구사항)
1. **Data Freshness**: The "Recent" worker should yield results for the current week within minutes.
2. **Efficiency**: Double the worker capacity for address collection during backfill peaks.

---

## 3. Specification & Conflict Review (명세 및 충돌 검토)

### Conflicts & Contradictions (모순점 및 충돌 여부)
- **Overlap Risk**: If the midpoint is not precisely calculated, there's a risk of collecting the same date twice.
  - *Mitigation*: Use strict bounds `[0, days//2]` and `[days//2, days]`.
- **Database Connection Pool**: Doubling workers might strain the DB connection pool.
  - *Check*: Current pool size is sufficient for 2-4 concurrent workers.
- **Naver Blocking**: Two workers hitting the same stock query simultaneously might increase the risk of CAPTCHA/blocking.
  - *Mitigation*: Ensure VPN rotation (already implemented) is robust and workers handle 403/429 gracefully.

### Redundancy & Inclusion (중복 및 포함 여부)
- **Daily Job Conflict**: Will this replace the `daily_address_worker`?
  - *Clarification*: No. `daily_address_worker` handles **New News** as it happens (Today's data). Parallel backfill handles **Historical News** (Yesterday and older). They are complementary.
- **Forward vs Backward**: The current `is_incremental` logic in `handle_job` is based on whether backfill was *ever* completed.
  - *Refactor needed*: We should specify the `direction` explicitly in the job parameters instead of inferring it.

---

## 4. Derived Requirements for Implementation (구현 요구사항)

1. [CODE] Update `JobManager` to create two sub-jobs for a single backfill request (or a single parent job with two tasks).
2. [CODE] Update `AddressCollector` to use a `direction` parameter (`forward` or `backward`).
3. [INFRA] Add a second `address_worker` instance in `docker-compose.yml`.
4. [DB] Ensure `tb_news_url` unique constraints handle potential overlaps.
