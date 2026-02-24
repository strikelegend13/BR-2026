# AwakenSecurity Architecture (Draft)

## Modules
- **electron-app/**: Desktop UI, user interaction, and local event display.
- **python-agent/**: Monitors screen, runs OCR and ML, communicates with Electron and backend.
- **backend/**: FastAPI server for buddy system, user management, and coordination.

## Data Flow

```
Electron App ⇄ Python Agent ⇄ Backend (buddy system)
```
- Electron and Python Agent communicate locally (IPC, HTTP, or sockets).
- Python Agent syncs with backend for buddy features and coordination.

## Security Notes
- Local-first: All monitoring and ML run on the user's device.
- Logs and sensitive data are **never** stored raw in the cloud.
- Only minimal, necessary metadata is sent to backend for buddy/accountability features.

---
This is a living document. Please update as the architecture evolves.
