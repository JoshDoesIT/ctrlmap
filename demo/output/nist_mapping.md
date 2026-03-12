# Compliance Mapping Results

## AC-1 — Policy and Procedures

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks policy documentation for AC-1: Policy and Procedures, which mandates the development, documentation, and dissemination of access control policies and procedures. This absence directly results in non-compliance with the security control requirement.

---

## AC-2 — Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (1.00)

**Rationale:** The provided policy excerpt focuses on assigning access rights based on job classification and function, adhering to the principle of least privilege. It also mandates documenting all access permissions in an access control matrix that maps roles to specific system privileges. However, it does not explicitly define or document types of accounts allowed or prohibited within the system.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 3.1  Role-Based Access Control (RBAC) | Access rights must be assigned based on job classification and function, following the principle of least privilege. ... |

---

## AC-2(1) — Automated System Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks policy documentation that addresses the automated management of system accounts as required by AC-2(1). This means there are no established procedures or guidelines for automating account creation, modification, and deletion processes, which is a critical aspect of security control.

---

## SC-28 — Protection of Information at Rest

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a specific policy addressing the protection of information at rest, which includes both confidentiality and integrity. To address SC-28, the organization needs to develop or update an existing policy that outlines procedures for securing data stored in various systems and media types.

---

