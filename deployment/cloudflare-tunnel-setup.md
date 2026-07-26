# Cloudflare Tunnel + Access — Watson dashboard

Exposes the Watson dashboard at `https://watson.<yourdomain>` through a
Cloudflare Tunnel, gated by Cloudflare Access to a single email (you).

**Why this design:** the Pi's network blocks UDP, so Tailscale can only relay
(slow, lossy). `cloudflared` makes an *outbound-only* TCP/443 connection to
Cloudflare's edge — no inbound ports, no router changes, works through
CGNAT/UDP-blocked networks. Auth (login) is handled entirely by Cloudflare
Access; the app itself stays auth-free.

## Request path

```
browser -> Cloudflare edge (TLS + Access login gate)
        -> tunnel -> cloudflared (Pi) -> frontend:80 (Caddy)
        -> /api/* to backend:8000, else static SPA
```

## One-time setup

Prereq: a domain already added to Cloudflare (DNS managed by Cloudflare).

### 1. Create the tunnel (Zero Trust dashboard)
- Cloudflare dashboard -> **Zero Trust** -> **Networks -> Tunnels -> Create tunnel**.
- Connector type: **Cloudflared**. Name it `watson`.
- On the install screen, choose **Docker** and **copy the tunnel token** (the long
  string after `--token`). You only need the token; the compose service already
  runs the connector.

### 2. Add the token to the Pi's .env
On the Pi, in `/home/suban/Documents/watson/.env`:
```
CLOUDFLARE_TOKEN=<paste the tunnel token>
```

### 3. Route the hostname to the frontend
- In the tunnel's **Public DNS** tab -> **Add a public hostname**:
  - Subdomain/domain: `watson.<yourdomain>`
  - Service **Type**: `HTTP`
  - **URL**: `frontend:80`
- Save. Cloudflare auto-creates the proxied DNS record.

### 4. Gate it with Access (only you)
- Zero Trust -> **Access -> Applications -> Add an application -> Self-hosted**.
- Application domain: `watson.<yourdomain>`.
- Add a policy: Action **Allow**, selector **Emails** = your address.
- Pick a login method (Google, or one-time PIN by email). Save.

### 5. Deploy
Push to `main` (CI deploys) or on the Pi:
```
bash deployment/deploy.sh
```
Verify the connector is healthy:
```
docker logs watson-bot-cloudflared-1 --tail 20   # expect "Registered tunnel connection"
```
In the dashboard the tunnel should show **HEALTHY**. Open
`https://watson.<yourdomain>` -> Cloudflare login -> dashboard.

## Adding more hostnames later
Same tunnel serves any number of hostnames. For each: add an entry under the
**Public DNS** tab pointing at the internal service (`service:port` on the
`back` network).
- **Private** (only you): also create an Access application for that hostname.
- **Public** (anyone): do NOT create an Access application — leave it ungated.

## Notes / gotchas
- `--protocol http2` in prod.yml forces TCP. Do not switch to QUIC — the Pi's
  network blocks UDP, so QUIC would fail.
- Access is enforced at Cloudflare's edge. Don't expose the same app through an
  ungated side door (e.g. publishing a host port on the Pi) or you bypass the
  gate. The frontend service publishes no host port — cloudflared reaches it
  only over the internal `back` network.
- Tailscale can stay installed for SSH admin (`tailscale up --ssh`); it does not
  conflict with the tunnel.
