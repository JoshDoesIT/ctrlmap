# Compliance Mapping Results

## AC-1 — Policy and Procedures

**Framework:** NIST-800-53 | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The policy text provides evidence for developing and documenting access control policies and procedures, but it does not explicitly mention disseminating these policies and procedures.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 3.1  Role-Based Access Control (RBAC) | Access rights must be assigned based on job classification and function, following the principle of least privilege. ... |

---

## AC-2 — Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.75)

**Rationale:** The policy text addresses aspects related to privileged access restrictions, separate credentials usage, and logging requirements. However, it does not explicitly define or document the specific types of accounts allowed or prohibited as required by AC-2.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 3.1  Role-Based Access Control (RBAC) | Access rights must be assigned based on job classification and function, following the principle of least privilege. ... |
| 2 | access_control_policy.pdf | 2 | 3.2  Privileged Access Management | Administrative and privileged access must be restricted to personnel whose job duties specifically require such acces... |
| 3 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | In cases where shared accounts are technically unavoidable (e.g., certain legacy systems), compensating controls incl... |

---

## AC-2(1) — Automated System Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The security control AC-2(1) requires that system accounts are managed using automated mechanisms to ensure efficiency and reduce human error. Without corresponding policy documentation in the organization's library, there is no guidance or mandate for implementing such automation, leading to a lack of standardization and potential vulnerabilities. To address this gap, the organization needs to create policies that specify requirements for automated account management systems, including procedures for creating, modifying, disabling accounts, and ensuring regular audits of these processes.

---

## SC-28 — Protection of Information at Rest

**Framework:** NIST-800-53 | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses the protection of information at rest by requiring encryption for all cardholder data stored across various mediums. This provides sufficient evidence to cover the confidentiality and integrity requirements specified in SC-28.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 2 | 1  Purpose and Scope | It covers data classification, encryption standards, key management, data retention, and secure disposal procedures. |
| 2 | data_protection_policy.pdf | 2 | 3.1  Encryption Standards | Database-level encryption using Transparent Data Encryption (TDE) is required for all production databases containing... |
| 3 | data_protection_policy.pdf | 2 | 3.1  Encryption Standards | All cardholder data stored in databases, file systems, backup media, and portable storage devices must be encrypted u... |

---

