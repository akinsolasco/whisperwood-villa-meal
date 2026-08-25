# Enhanced Living Whisperwood Smart Label Support Site

Static documentation and support portal for staff training, troubleshooting,
installation, recovery, and technical implementation notes.

## Local preview

From this folder:

```powershell
python -m http.server 8092
```

Then open:

```text
http://127.0.0.1:8092/
```

## Demo Raspberry Pi deployment

The first demo deployment serves the portal from:

```text
/opt/whisperwood-support-portal
```

using a systemd service named:

```text
whisperwood-support-portal.service
```

Suggested review link:

```text
http://192.168.2.37:8092/
```

## IT domain/server deployment

Use:

```text
README_IT_DEPLOYMENT.md
```

That guide explains how to host the site on an IT server, connect a custom
domain, enable HTTPS, and keep the site connected to GitHub so future manual
changes can be pulled without sending another zip.

## Content still expected

- Final facility support contact details.
- Circuit drawings and pin map.
- Approved hardware replacement policy.
- Final screenshots after UI stabilises.
- Final firmware upload and OTA policy.
