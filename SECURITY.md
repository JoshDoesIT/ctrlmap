# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in ctrlmap, please report it responsibly using [GitHub Security Advisories](https://github.com/JoshDoesIT/ctrlmap/security/advisories/new). This ensures the report stays private until a fix is available.

**Please do not open a public issue for security vulnerabilities.**

### What to Include

- A clear description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested fixes (optional)

### Response Timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 1 week
- **Fix or mitigation**: depends on severity, but we aim for 30 days for critical issues

### Scope

ctrlmap runs entirely locally with no network calls to external services. The primary security concerns are:

- Dependency vulnerabilities in the Python supply chain
- File handling and path traversal in document parsing
- Local data integrity and access control
- LLM prompt injection via adversarial PDF content that could manipulate compliance outputs

### Out of Scope

- Vulnerabilities in Ollama itself (report those to the Ollama project)
- Issues with the underlying operating system or Python runtime
