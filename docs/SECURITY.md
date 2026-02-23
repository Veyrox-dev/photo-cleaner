# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.3.x   | :white_check_mark: |
| 2.2.x   | :white_check_mark: |
| < 2.2   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 1. **DO NOT** Open a Public Issue

Security vulnerabilities should not be disclosed publicly until a fix is available.

### 2. Report Privately

Send an email to: **security@photocleaner.example.com** (replace with actual email)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### 3. Response Timeline

- **24 hours**: Acknowledgment of report
- **72 hours**: Initial assessment
- **7 days**: Fix or mitigation plan
- **30 days**: Public disclosure (after fix is released)

## Security Considerations

### Local File Access

PhotoCleaner requires file system access to:
- Read image files
- Write database files
- Move files to trash

**Mitigation**: Run with least privilege, review file paths before processing.

### License System

License keys are validated locally using HMAC-SHA256:
- Keys are NOT transmitted over network
- No "phone home" functionality
- Keys can be revoked by removing license file

**Note**: License system is for feature gating, not security. Do not rely on it for access control in production environments.

### Database Security

SQLite databases store:
- File paths
- Analysis results
- Cache data
- License information

**Mitigation**: 
- Databases are stored locally
- No sensitive personal data
- Can be encrypted at filesystem level

### Dependency Security

We monitor dependencies for known vulnerabilities:
- Pillow: Image processing (potential malicious images)
- OpenCV: Computer vision (potential buffer overflows)
- MediaPipe: Machine learning (potential model poisoning)

**Mitigation**: Pin versions in requirements.txt, update regularly.

## Best Practices

### For Users

1. **Download from official sources only**
2. **Verify checksums** before installation
3. **Keep software updated** to latest version
4. **Review file paths** before running batch operations
5. **Backup important files** before bulk deletion

### For Developers

1. **Never commit secrets** (API keys, passwords, etc.)
2. **Validate all user inputs** (file paths, parameters)
3. **Use parameterized queries** for SQL
4. **Sanitize file paths** to prevent directory traversal
5. **Handle exceptions gracefully** without exposing internals

## Known Limitations

### Not Cryptographically Secure

- License keys use HMAC but can be reverse-engineered
- Cache uses SHA1 (deprecated for crypto, OK for hashing)
- No encryption of stored data

**Intended Use**: Personal/organizational photo management, not high-security environments.

### File System Access

- PhotoCleaner can read/write/delete files
- No sandboxing or isolation
- Runs with user's permissions

**Recommendation**: Review operations before confirming deletions.

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities.

Hall of Fame:
- TBD (Be the first!)

---

Last updated: 2026-01-25
