#!/bin/bash
# Validate TLS Certificate Chain
# Validates remote TLS endpoint certificate chain

set -euo pipefail

ENDPOINT="${1:-}"
CA_BUNDLE="${2:-/etc/ssl/certs/ca-certificates.crt}"
VERBOSE=false
CHECK_REVOCATION=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ca-bundle)
            CA_BUNDLE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --check-revocation)
            CHECK_REVOCATION=true
            shift
            ;;
        *)
            if [ -z "$ENDPOINT" ]; then
                ENDPOINT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$ENDPOINT" ]; then
    echo "Usage: $0 <host:port> [--ca-bundle <path>] [--verbose] [--check-revocation]"
    echo ""
    echo "Examples:"
    echo "  $0 example.com:443"
    echo "  $0 example.com:443 --ca-bundle /path/to/ca-bundle.pem"
    echo "  $0 example.com:443 --verbose --check-revocation"
    exit 1
fi

# Parse host and port
HOST=$(echo "$ENDPOINT" | cut -d: -f1)
PORT=$(echo "$ENDPOINT" | cut -d: -f2)

if [ -z "$PORT" ]; then
    PORT=443
fi

echo "=== TLS Chain Validation ==="
echo "Endpoint: $HOST:$PORT"
echo "CA Bundle: $CA_BUNDLE"
echo ""

# Check if CA bundle exists
if [ ! -f "$CA_BUNDLE" ]; then
    echo "Warning: CA bundle not found: $CA_BUNDLE"
    echo "Using system default..."
    CA_BUNDLE=""
fi

# Get certificate chain
echo "Retrieving certificate chain..."
CERT_OUTPUT=$(timeout 10 openssl s_client -connect "$HOST:$PORT" -showcerts -CAfile "$CA_BUNDLE" </dev/null 2>&1)

if [ $? -ne 0 ]; then
    echo "Error: Failed to connect to $HOST:$PORT"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify hostname and port are correct"
    echo "  2. Check network connectivity"
    echo "  3. Verify firewall rules"
    exit 1
fi

# Extract certificate
echo "$CERT_OUTPUT" | openssl x509 -outform PEM > /tmp/cert_$$.pem 2>/dev/null

if [ ! -s /tmp/cert_$$.pem ]; then
    echo "Error: Failed to extract certificate"
    exit 1
fi

# Display certificate information
echo ""
echo "Certificate Information:"
echo "========================"
echo ""

openssl x509 -in /tmp/cert_$$.pem -noout -text | grep -E "(Subject:|Issuer:|Not Before|Not After|DNS:|IP Address:)" | head -20

# Check validity
echo ""
echo "Validity Check:"
echo "==============="
CURRENT_DATE=$(date +%s)
NOT_AFTER=$(openssl x509 -in /tmp/cert_$$.pem -noout -enddate | cut -d= -f2)
NOT_AFTER_EPOCH=$(date -d "$NOT_AFTER" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$NOT_AFTER" +%s 2>/dev/null || echo "0")

if [ "$NOT_AFTER_EPOCH" != "0" ] && [ "$CURRENT_DATE" -gt "$NOT_AFTER_EPOCH" ]; then
    echo "✗ Certificate EXPIRED"
    echo "  Expired on: $NOT_AFTER"
elif [ "$NOT_AFTER_EPOCH" != "0" ]; then
    DAYS_LEFT=$(( ($NOT_AFTER_EPOCH - $CURRENT_DATE) / 86400 ))
    echo "✓ Certificate VALID"
    echo "  Expires: $NOT_AFTER ($DAYS_LEFT days remaining)"
    
    if [ "$DAYS_LEFT" -lt 30 ]; then
        echo "  ⚠ Warning: Certificate expires soon!"
    fi
fi

# Check hostname
echo ""
echo "Hostname Check:"
echo "==============="
CERT_CN=$(openssl x509 -in /tmp/cert_$$.pem -noout -subject | sed -n 's/.*CN=\([^,]*\).*/\1/p')
CERT_SAN=$(openssl x509 -in /tmp/cert_$$.pem -noout -text | grep -A 1 "Subject Alternative Name" | tail -1)

if echo "$CERT_SAN" | grep -q "$HOST" || [ "$CERT_CN" = "$HOST" ]; then
    echo "✓ Hostname MATCHES"
    echo "  Certificate CN: $CERT_CN"
    echo "  SAN: $CERT_SAN"
else
    echo "✗ Hostname MISMATCH"
    echo "  Connecting to: $HOST"
    echo "  Certificate CN: $CERT_CN"
    echo "  SAN: $CERT_SAN"
fi

# Validate chain
echo ""
echo "Chain Validation:"
echo "=================="
if [ -n "$CA_BUNDLE" ] && [ -f "$CA_BUNDLE" ]; then
    CHAIN_VALID=$(echo "$CERT_OUTPUT" | openssl verify -CAfile "$CA_BUNDLE" /tmp/cert_$$.pem 2>&1)
    if echo "$CHAIN_VALID" | grep -q "OK"; then
        echo "✓ Certificate chain VALID"
    else
        echo "✗ Certificate chain INVALID"
        echo "$CHAIN_VALID"
    fi
else
    CHAIN_VALID=$(echo "$CERT_OUTPUT" | openssl verify /tmp/cert_$$.pem 2>&1)
    if echo "$CHAIN_VALID" | grep -q "OK"; then
        echo "✓ Certificate chain VALID (using system trust store)"
    else
        echo "✗ Certificate chain INVALID or UNTRUSTED"
        echo "$CHAIN_VALID"
        echo ""
        echo "Common issues:"
        echo "  - Self-signed certificate"
        echo "  - Untrusted CA"
        echo "  - Incomplete certificate chain"
    fi
fi

# Check revocation (if requested)
if [ "$CHECK_REVOCATION" = true ]; then
    echo ""
    echo "Revocation Check:"
    echo "================="
    OCSP_OUTPUT=$(openssl s_client -connect "$HOST:$PORT" -status </dev/null 2>&1 | grep -A 10 "OCSP")
    if echo "$OCSP_OUTPUT" | grep -q "revoked"; then
        echo "✗ Certificate REVOKED"
    elif echo "$OCSP_OUTPUT" | grep -q "good"; then
        echo "✓ Certificate NOT REVOKED"
    else
        echo "? Revocation status UNKNOWN (OCSP not available)"
    fi
fi

# Verbose output
if [ "$VERBOSE" = true ]; then
    echo ""
    echo "Verbose Certificate Details:"
    echo "============================"
    openssl x509 -in /tmp/cert_$$.pem -noout -text
fi

# Cleanup
rm -f /tmp/cert_$$.pem

echo ""
echo "=== Validation Complete ==="
