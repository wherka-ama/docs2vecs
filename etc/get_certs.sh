#!/bin/bash
openssl s_client -connect astral.sh:443 -showcerts </dev/null | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p'