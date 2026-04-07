# API Requirements Quality Checklist: SDD 阶段流水线

**Purpose**: Validate API contract quality and completeness
**Created**: 2026-04-07
**Feature**: [contracts/sdd-stage-contract.md](../contracts/sdd-stage-contract.md)

## API Completeness

- [ ] CHK001 - Are all API endpoints defined (trigger, approve, query)? [Completeness, contracts]
- [ ] CHK002 - Are request body formats specified for all endpoints? [Completeness, contracts]
- [ ] CHK003 - Are response formats specified with all required fields? [Completeness, contracts]
- [ ] CHK004 - Are error response formats defined for each failure scenario? [Completeness, Gap]

## API Clarity

- [ ] CHK005 - Are stage names explicitly enumerated in the contract? [Clarity, contracts]
- [ ] CHK006 - Is the `next_stage` return value documented when approval occurs? [Clarity, contracts]
- [ ] CHK007 - Are status values (PENDING, RUNNING, etc.) consistently named across API? [Clarity, contracts]

## API Consistency

- [ ] CHK008 - Do trigger and approve endpoints use consistent status value casing (uppercase)? [Consistency, contracts vs data-model]
- [ ] CHK009 - Are HTTP status codes specified for each response type? [Consistency, Gap]

## Validation Rules

- [ ] CHK010 - Are validation rules documented in the API contract? [Completeness, contracts §验证规则]
- [ ] CHK011 - Is the前置条件 "trigger requires APPROVED or PENDING state" documented? [Completeness, contracts]
- [ ] CHK012 - Is the "reject requires comments" rule documented? [Completeness, contracts]

## Edge Cases

- [ ] CHK013 - Are requirements defined for triggering a stage that's already RUNNING? [Edge Case, Gap]
- [ ] CHK014 - Are requirements defined for approving a stage that's not WAITING_APPROVAL? [Edge Case, Gap]
- [ ] CHK015 - Are requirements defined for concurrent approval attempts on the same stage? [Edge Case, Gap]

## Non-Functional

- [ ] CHK016 - Are timeout values specified for DeerFlow execution? [Performance, spec.md]
- [ ] CHK017 - Are rate limiting requirements documented for concurrent Issues? [Performance, Gap]

## Notes

- Focus on API contract quality validation
- Gap items require spec updates before implementation
