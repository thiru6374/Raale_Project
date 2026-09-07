# Stakeholder Validation

## Target Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| District Health Officer | Decision maker | Accurate prioritisation; no wasted team capacity |
| Field Outreach Coordinators | Operations | Clear, actionable neighbourhood lists |
| Public Health Analysts | Analysts | Transparent, explainable scores |
| Community Representatives | Advocates | Equitable coverage for all populations |
| IT/System Administrators | Operators | Safe override mechanism; audit trail |

## Validation Questions by Stakeholder

### District Health Officer
- ✅ Can the system explain *why* a neighbourhood is rated Extreme vs High?
- ✅ Can a human override the system's decision with a logged reason?
- ✅ Is the optimiser constrained to never exceed team capacity?

### Field Outreach Coordinators
- ✅ Is the list of selected neighbourhoods sortable by priority?
- ✅ Does each neighbourhood have a specific advisory, not a generic one?
- ✅ Are neighbourhoods with unreliable data clearly marked (MANUAL_REVIEW)?

### Public Health Analysts
- ✅ Is there a baseline comparison to prove the multi-factor model adds value?
- ✅ Are the risk weights configurable without touching the code?
- ✅ Are experiment results saved to a file for post-hoc analysis?

### Community Representatives
- ✅ Is the system checked for bias against mobile populations?
- ✅ Is there a mechanism to flag and correct unfair outcomes?
- ✅ Are the advisories in plain language, not jargon?

### IT/System Administrators
- ✅ Is every override logged with a timestamp, user ID, and reason?
- ✅ Does the system fail safely rather than producing wrong answers silently?
- ✅ Are all configurable parameters in a single location?

## Known Limitations (Phase 1–13)

1. **Synthetic Data**: The generator simulates Chennai conditions but does not connect to real Open-Meteo, satellite, or census APIs. This is planned for a future phase.
2. **No Authentication**: The override system captures a `user_id` string but does not enforce actual login. A future phase would integrate with an identity provider.
3. **PuLP deprecation warnings**: The CBC solver API is showing deprecation warnings for PuLP 4.0 compatibility. The upgrade path is replacing `PULP_CBC_CMD` with `COIN_CMD`.
4. **Static rule-based messaging**: The localised advisory engine uses deterministic rules. A future phase may use an LLM API for richer, more nuanced language.

## Planned Future Improvements

- Real API integration (Open-Meteo for temperature, Census for demographics)
- Multi-language advisory support (Tamil, English)
- Role-based access control for override authorisation
- Time-series risk tracking (daily/weekly trends)
- SQLite or PostgreSQL for persistent audit storage
