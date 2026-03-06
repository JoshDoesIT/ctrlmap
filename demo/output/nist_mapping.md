# Compliance Mapping Results

## AC-1 — Policy and Procedures

**Framework:** NIST-800-53 | **Verdict:** ✅ Compliant (0.90)

**Rationale:** The policy text clearly outlines the principles and procedures for developing and disseminating access control policies and procedures, including restricting administrative and privileged access, reviewing user access rights regularly, assigning access based on job classification and function, and documenting all access permissions in an access control matrix.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 3.2  Privileged Access Management | Administrative and privileged access must be restricted to personnel whose job duties specifically require such acces... |
| 2 | access_control_policy.pdf | 3 | 4  Periodic Access Reviews | User access rights must be reviewed at least every six months to verify that access remains appropriate for the user'... |
| 3 | access_control_policy.pdf | 2 | 3.1  Role-Based Access Control (RBAC) | Access rights must be assigned based on job classification and function, following the principle of least privilege. ... |

---

## AC-2 — Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.50)

**Rationale:** The policy text does not specifically address account management, including defining and documenting types of accounts allowed or prohibited for use within the system.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 4  Periodic Access Reviews | This policy establishes the requirements for managing access to Acme Corp information systems, applications, and data... |

---

## AC-2(1) — Automated System Account Management

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks policy documentation outlining its approach to automated system account management, making it difficult to ensure that system accounts are properly managed and secured. Specifically, there is no guidance on the use of automated mechanisms for account creation, modification, or deletion. This gap makes it challenging to maintain accountability, track changes, and detect potential security incidents related to system accounts.

---

## SC-28 — Protection of Information at Rest

**Framework:** NIST-800-53 | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization's lack of policy coverage for protecting information at rest (SC-28) may result in unauthorized access, modification, or theft of sensitive data stored on devices, media, or other storage systems. To address this gap, a new policy should be created outlining the procedures for encrypting and securing sensitive data at rest, including measures such as full-disk encryption, secure deletion practices, and proper disposal of outdated media.

---

