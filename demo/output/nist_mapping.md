# Compliance Mapping Results

## AC-1 — Policy and Procedures

**Framework:** NIST-800-53 | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk directly addresses the requirement by establishing a comprehensive access control policy that applies broadly to all relevant personnel requiring access to Acme Corp's systems and CDE.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 1  Purpose and Scope | This policy establishes the requirements for managing access to Acme Corp information systems, applications, and data... |

---

## AC-2 — Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (1.00)

**Rationale:** No policy documentation exists to define and document the types of accounts allowed and specifically prohibited for use within the system. The organization needs an account management policy that outlines the types of user accounts (e.g., administrative, standard, guest) permitted, as well as any specific accounts or roles that are explicitly forbidden.

---

## AC-2(1) — Automated System Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (1.00)

**Rationale:** No policy documentation exists to support automated system account management as required by AC-2(1). The organization needs a policy that outlines the procedures for implementing and maintaining automated mechanisms for managing system accounts, including account creation, modification, deactivation, and deletion processes.

---

## SC-28 — Protection of Information at Rest

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.20)

**Rationale:** The excerpt describes the purpose and scope of data protection but does not provide specific measures or mechanisms for protecting information at rest. It mentions encryption standards and key management, which are relevant to SC-28, but lacks detailed implementation details.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 2 | 1  Purpose and Scope | This policy defines the requirements for protecting sensitive data including cardholder data (CHD), personally identi... |

---

