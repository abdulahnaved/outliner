# Lab self-signed certificates

Used by all HTTPS lab targets (good, bad_headers, bad_cors, bad_cookies).

## Generate on Mac/Linux

```bash
cd lab/certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout localhost.key -out localhost.crt \
  -subj "/CN=localhost"
```

Then start the lab with `docker compose up -d` from `lab/`. Browsers and clients will show a self-signed cert warning; for dev/lab use only.
