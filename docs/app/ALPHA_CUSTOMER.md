# Alpha Customer

This one-pager defines the primary **customer** (or user) for the Alpha release of QASIC Engineering-as-Code. The answer drives prioritization and where we allocate engineering and budget.

See also [ALPHA_SCOPE.md](ALPHA_SCOPE.md) and [PROGRAM_ACTION_ITEMS.md](PROGRAM_ACTION_ITEMS.md).

---

## Primary customer: Internal hardware engineering team

**Decision made.** Alpha is an internal tool for our own hardware team to accelerate tapeouts (circuit → routing → inverse → HEaC → GDS).

**Implications:** Prioritize pipeline stability, GDS success rate, runbooks, and integration with internal CAD/fab workflows. Defer multi-tenant and external UX polish; self-serve onboarding and external API polish can wait.

| Option | Description | Implications |
|--------|-------------|--------------|
| **Internal hardware engineering team** (chosen) | Alpha is an internal tool for our own hardware team to accelerate tapeouts (circuit → routing → inverse → HEaC → GDS). | Prioritize: golden path reliability, runbooks, integration with internal CAD/fab workflows. Less focus on multi-tenant or external UX. |
| **External / SaaS foundation** | Alpha is the foundation of an external-facing platform (e.g. customers submit circuits, get GDS or reports). | Prioritize: API stability, auth, quotas, and clear external docs. Higher bar on security and isolation. |
| **Hybrid** | Internal first, with a path to external (e.g. same API, internal-only during Alpha; external beta later). | Document the internal vs external timeline and what must be true before external access. |

---

## Implications for prioritization

- **Internal (current):** Budget and engineering hours go to pipeline stability, GDS success rate, and internal feedback loops. External polish and self-serve onboarding can wait.
- **If external later:** Budget and engineering hours would shift to API contracts, auth, rate limits, and documentation. Internal-only features (e.g. deep integration with internal PDK) may be deferred.
- **If hybrid later:** Explicitly list what is "internal Alpha" vs "external-ready" and assign ownership and dates in [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md).

---

## Next step

The 45-min kickoff can still be used to confirm scope and roadmap (e.g. [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md)) rather than customer choice.
