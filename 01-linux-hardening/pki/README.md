# PKI Trust Inspection Module

This module provides tools for inspecting Linux trust stores and validating TLS certificate chains.

## Overview

The PKI module helps security engineers:
- Inspect system CA certificate stores
- Validate TLS certificate chains
- Identify common certificate issues (expired, wrong hostname, untrusted CA)
- Understand trust relationships

## Tools

### 1. Trust Store Inspection

#### `inspect-trust-store.sh`
Lists all CA certificates in the system trust store.

```bash
./inspect-trust-store.sh
```

**Output**: Lists all CA certificates with subject, issuer, and validity dates.

#### `find-certificate.sh`
Finds a certificate by subject or issuer.

```bash
./find-certificate.sh "CN=Example CA"
./find-certificate.sh "O=Let's Encrypt"
```

### 2. TLS Chain Validation

#### `validate-tls-chain.sh`
Validates a remote TLS endpoint's certificate chain.

```bash
# Basic validation
./validate-tls-chain.sh example.com:443

# With custom CA bundle
./validate-tls-chain.sh example.com:443 --ca-bundle /path/to/ca-bundle.pem

# Verbose output
./validate-tls-chain.sh example.com:443 --verbose
```

**Output**: Certificate details, chain validation status, and any issues found.

## Common Failure Cases

### 1. Expired Certificate

**Symptoms**:
```
certificate has expired
notAfter: Dec 31 23:59:59 2023 GMT
```

**Detection**:
```bash
./validate-tls-chain.sh example.com:443 | grep -i expired
```

**Remediation**: Renew certificate with CA.

### 2. Hostname Mismatch

**Symptoms**:
```
Hostname mismatch: certificate is for *.example.com but connecting to test.example.com
```

**Detection**:
```bash
./validate-tls-chain.sh example.com:443 | grep -i "hostname\|subject alternative name"
```

**Remediation**: Use correct hostname or update certificate with correct SAN.

### 3. Untrusted CA

**Symptoms**:
```
self signed certificate
unable to get local issuer certificate
```

**Detection**:
```bash
./validate-tls-chain.sh example.com:443 | grep -i "untrusted\|self signed\|issuer"
```

**Remediation**: 
- Add CA certificate to system trust store
- Use publicly trusted CA
- Configure custom CA bundle

### 4. Incomplete Certificate Chain

**Symptoms**:
```
unable to get local issuer certificate
certificate chain too short
```

**Detection**:
```bash
./validate-tls-chain.sh example.com:443 | grep -i "chain\|issuer"
```

**Remediation**: Ensure intermediate certificates are included in server configuration.

### 5. Revoked Certificate

**Symptoms**:
```
certificate revoked
OCSP response: revoked
```

**Detection**:
```bash
./validate-tls-chain.sh example.com:443 --check-revocation
```

**Remediation**: Replace revoked certificate.

## Linux Trust Store Locations

### Ubuntu/Debian
- System CA bundle: `/etc/ssl/certs/ca-certificates.crt`
- Individual CAs: `/etc/ssl/certs/`
- Update command: `update-ca-certificates`

### RHEL/CentOS
- System CA bundle: `/etc/pki/tls/certs/ca-bundle.crt`
- Individual CAs: `/etc/pki/ca-trust/source/anchors/`
- Update command: `update-ca-trust`

### Manual Inspection
```bash
# List all certificates
ls -la /etc/ssl/certs/

# View certificate details
openssl x509 -in /etc/ssl/certs/ca-certificates.crt -text -noout

# Search for specific CA
grep -r "Let's Encrypt" /etc/ssl/certs/
```

## OpenSSL Commands Reference

### Basic Certificate Inspection
```bash
# Get certificate from remote server
openssl s_client -connect example.com:443 -showcerts </dev/null 2>/dev/null

# Save certificate to file
openssl s_client -connect example.com:443 -showcerts </dev/null 2>/dev/null | openssl x509 -outform PEM > cert.pem

# View certificate details
openssl x509 -in cert.pem -text -noout

# Check certificate validity
openssl x509 -in cert.pem -noout -dates
```

### Chain Validation
```bash
# Validate with system trust store
openssl s_client -connect example.com:443 -CAfile /etc/ssl/certs/ca-certificates.crt </dev/null

# Validate with custom CA bundle
openssl s_client -connect example.com:443 -CAfile custom-ca-bundle.pem </dev/null

# Check certificate chain
openssl s_client -connect example.com:443 -showcerts </dev/null | openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt -
```

### OCSP Checking
```bash
# Check certificate revocation via OCSP
openssl s_client -connect example.com:443 -status </dev/null 2>&1 | grep -A 10 "OCSP"
```

## Troubleshooting

### Certificate Not Trusted
1. Check if CA is in system trust store
2. Verify certificate chain is complete
3. Check certificate validity dates
4. Verify hostname matches certificate

### Connection Errors
1. Verify network connectivity
2. Check firewall rules
3. Verify port is correct
4. Check if service is running

### Performance Issues
1. Use `-brief` flag for faster checks
2. Cache certificate information
3. Use parallel processing for multiple hosts

## Best Practices

1. **Regular Validation**: Schedule periodic certificate validation
2. **Monitoring**: Set up alerts for expiring certificates
3. **Documentation**: Maintain inventory of certificates and CAs
4. **Automation**: Automate certificate renewal where possible
5. **Testing**: Test certificate changes in non-production first

## Integration with Phase 1

The PKI module complements Linux hardening by:
- Validating TLS endpoints used by services
- Ensuring secure communication channels
- Identifying misconfigured certificates
- Supporting compliance requirements (TLS configuration)

## References

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [RFC 5280 - X.509 Certificate Profile](https://tools.ietf.org/html/rfc5280)
- [Mozilla CA Certificate Policy](https://www.mozilla.org/en-US/about/governance/policies/security-group/certs/)
