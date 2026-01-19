#!/bin/bash
# Find Certificate in Trust Store
# Searches for certificates by subject or issuer

set -euo pipefail

SEARCH_TERM="${1:-}"
TRUST_STORE="${2:-/etc/ssl/certs/ca-certificates.crt}"

if [ -z "$SEARCH_TERM" ]; then
    echo "Usage: $0 <search-term> [trust-store]"
    echo ""
    echo "Examples:"
    echo "  $0 \"CN=Example CA\""
    echo "  $0 \"Let's Encrypt\""
    echo "  $0 \"DigiCert\""
    exit 1
fi

if [ ! -f "$TRUST_STORE" ]; then
    echo "Error: Trust store not found: $TRUST_STORE"
    exit 1
fi

echo "=== Searching Trust Store ==="
echo "Search Term: $SEARCH_TERM"
echo "Trust Store: $TRUST_STORE"
echo ""

# Extract certificates and search
FOUND=0

awk -v search="$SEARCH_TERM" '
BEGIN {
    cert = ""
    in_cert = 0
    cert_num = 0
}
/BEGIN CERTIFICATE/ {
    in_cert = 1
    cert = $0 "\n"
    next
}
/END CERTIFICATE/ {
    cert = cert $0 "\n"
    in_cert = 0
    cert_num++
    
    # Extract certificate info
    cmd = "echo \"" cert "\" | openssl x509 -noout -subject -issuer -dates -fingerprint 2>/dev/null"
    subject = ""
    issuer = ""
    notBefore = ""
    notAfter = ""
    fingerprint = ""
    
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
        if (line ~ /^SHA1 Fingerprint/) {
            gsub(/^SHA1 Fingerprint=/, "", line)
            fingerprint = line
        }
    }
    close(cmd)
    
    # Check if search term matches
    if (subject ~ search || issuer ~ search) {
        print "Certificate #" cert_num ":"
        print "  Subject:     " subject
        print "  Issuer:      " issuer
        print "  Valid From:  " notBefore
        print "  Valid To:    " notAfter
        print "  Fingerprint: " fingerprint
        print "  ---"
        found = 1
    }
    
    cert = ""
    next
}
in_cert {
    cert = cert $0 "\n"
}
END {
    if (!found) {
        print "No certificates found matching: " search
        exit 1
    }
}
' "$TRUST_STORE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Search Complete ==="
else
    echo ""
    echo "No certificates found matching: $SEARCH_TERM"
    exit 1
fi
