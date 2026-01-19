#!/bin/bash
# Inspect Linux Trust Store
# Lists all CA certificates in the system trust store

set -euo pipefail

TRUST_STORE="${1:-/etc/ssl/certs/ca-certificates.crt}"

if [ ! -f "$TRUST_STORE" ]; then
    echo "Error: Trust store not found: $TRUST_STORE"
    echo ""
    echo "Common locations:"
    echo "  Ubuntu/Debian: /etc/ssl/certs/ca-certificates.crt"
    echo "  RHEL/CentOS:   /etc/pki/tls/certs/ca-bundle.crt"
    exit 1
fi

echo "=== Linux Trust Store Inspection ==="
echo "Trust Store: $TRUST_STORE"
echo ""

# Count certificates
CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "$TRUST_STORE" 2>/dev/null || echo "0")
echo "Total Certificates: $CERT_COUNT"
echo ""

# Extract and display certificate information
echo "Certificate Details:"
echo "===================="
echo ""

# Split certificates and display info
awk '
BEGIN {
    cert = ""
    in_cert = 0
}
/BEGIN CERTIFICATE/ {
    in_cert = 1
    cert = $0 "\n"
    next
}
/END CERTIFICATE/ {
    cert = cert $0 "\n"
    in_cert = 0
    
    # Extract certificate info using openssl
    cmd = "echo \"" cert "\" | openssl x509 -noout -subject -issuer -dates 2>/dev/null"
    while ((cmd | getline line) > 0) {
        if (line ~ /^subject=/) {
            gsub(/^subject=/, "", line)
            subject = line
        }
        if (line ~ /^issuer=/) {
            gsub(/^issuer=/, "", line)
            issuer = line
        }
        if (line ~ /^notBefore/) {
            gsub(/^notBefore=/, "", line)
            notBefore = line
        }
        if (line ~ /^notAfter/) {
            gsub(/^notAfter=/, "", line)
            notAfter = line
        }
    }
    close(cmd)
    
    print "Subject: " subject
    print "Issuer:  " issuer
    print "Valid:   " notBefore " to " notAfter
    print "---"
    
    cert = ""
    next
}
in_cert {
    cert = cert $0 "\n"
}
' "$TRUST_STORE" 2>/dev/null | head -100

if [ "$CERT_COUNT" -gt 20 ]; then
    echo ""
    echo "... (showing first 20 certificates, use grep to filter specific CAs)"
fi

echo ""
echo "=== Inspection Complete ==="
echo ""
echo "To find a specific certificate:"
echo "  ./find-certificate.sh \"CN=Example CA\""
