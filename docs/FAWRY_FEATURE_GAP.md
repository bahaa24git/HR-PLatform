# Vendor feature comparison

Reviewed 18 November 2026. These are public-documentation comparisons, not a claim of Fawry certification or complete parity. No vendor software, credentials or live financial service was connected.

## Verified source boundaries

- [Fawry HR Solutions](https://www.fawry.com/hr-solutions/) documents onboarding/payroll, payout integration, mobile employee requests, geolocation/machine/timesheet attendance and Arabic/English support. Our onboarding, payroll, geolocation and bilingual web workflows exist. This audit adds reviewed CSV timesheet imports. Native mobile apps, attendance-device connectors and Fawry payout integration are **missing**; no payout is simulated. The vendor's statutory-compliance claim is not a claim about this platform: Egyptian tax/social-insurance calculations remain **missing**, requiring a specified, independently reviewed statutory/payroll integration.
- [Fawry Business-HR Help Center](https://helpcenter.fawrypayday.com/) documents company setup, departments/geolocation configuration, employee loading/pay elements and shift setup. Our configuration, departments, employment records and salary components are **implemented**; reviewed attendance loading, holidays and corrections are now **implemented and tested**. General shift scheduling is **not relevant to this installation's fixed agreed 09:00–18:00 attendance policy** and was not substituted for that policy. Bulk employee onboarding beyond the existing HR entry/hiring workflow remains **partially implemented**.
- [Fawry's investment announcement](https://www.fawry.com/wp-content/uploads/2025/02/Investments-PR-Final-v2.pdf) identifies CodeZone business software in the expanded Fawry Business ecosystem. That association does not establish identical capabilities across every Fawry product.
- [CodeZone's official product overview](https://www.codezone-eg.com/en) describes centralized customer information/documents, lead tracking, sales-visit planning and campaign ROI analysis. Our accounts/contacts/private attachments, lead/deal conversion, scheduled meetings/activities and campaign metrics cover these broad categories. Client ad-spend attribution and company revenue remain separate. This is an **implemented category comparison**, not verified one-to-one product parity. Contract-backed invoice/receipt allocation and collection balances were missing locally and are now **implemented and tested**. Automatic external communications and a separate authenticated client portal remain **missing**.

## Local feature-gap decisions

| Capability | Classification after audit | Evidence / boundary |
|---|---|---|
| Employee records, contracts, history and onboarding | Already implemented; expiry display strengthened | Existing lifecycle tests; effective onboarding expiry retains original records |
| Attendance/leave/payroll | Previously partial; repaired | Pending-review guard, fresh approval calculation, audited corrections, actual classifications, holidays, CSV import |
| Recruitment and CV/interview/hire workflows | Already implemented | Backend lifecycle tests; HR decides hiring; no autonomous screening decision |
| Training effectiveness and skill development | Already implemented | Course, enrollment, attendance, pre/post and KPI evidence |
| Career path mapping/readiness | Missing; implemented in this audit | HR-defined role paths, recorded skill gaps/tenure; no automatic promotion |
| Confidential feedback/surveys/offboarding | Already implemented | Shared-case rules, anonymity thresholds, documented human approvals |
| CRM conversion/quotes/contracts | Already implemented; integrity strengthened | Won-deal conversion, reviewed quotation, preserved approved financial terms |
| Invoice/collections ledger | Missing; implemented in this audit | Contract-backed invoices, explicit receipt allocation, balances and PDF reports; not fiscal e-invoicing |
| Specialized AI orchestration | Previously partial; extended | Scoped multi-intent specialist context and wellbeing route; one configured model call, no autonomous mutation tools |
| External payouts, tax, insurance and fiscal e-invoicing | Missing / requires integration specification | No external transfers, legal compliance certification or fake integration |
| Hardware/native mobile/client portal | Missing | Responsive web is supported; these separate products are not claimed to exist |

Capabilities lacking vendor documentation were not invented. Vendor feature categories do not override the installation's agreed approval rules, permissions or data-protection boundaries.
