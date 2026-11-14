# ZOHRA PRODUCTION DEPLOYMENT & OPERATIONS GUIDE

## 1. Production Architecture (Single VPS Target)

For Launch (1–5 sites), Zohra runs on a single high-performance Linux VPS (e.g. 4-8 vCPU, 8-16 GB RAM) with containerized services:
- **reverse-proxy**: Caddy 2 or Nginx with strict security headers and TLS termination.
- **frontend**: Command Center Next.js UI (`:3000`).
- **api**: FastAPI application running 4 uvicorn workers (`:8000`).
- **worker pools**:
  - `worker-general`: discovery, trends, research.
  - `worker-publishing`: WordPress sync, media upload, schema injection.
  - `worker-analytics`: Search Console ingestion, decay detection.
  - `worker-optimization`: Content refresh, experiments, strategy updates.
- **beat**: Celery Beat scheduler registry.
- **postgres**: PostgreSQL 16 with persistent volume and connection pooling.
- **redis**: Redis 7 with AOF persistence.
- **backup-runner**: Daily automated encrypted backup runner.

---

## 2. First-Run Production Setup Checklist

1. **Server Preparation**:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin curl
   sudo usermod -aG docker $USER
   ```
2. **Clone & Configure**:
   ```bash
   git clone https://github.com/your-org/zohra-publisher.git /opt/zohra-publisher
   cd /opt/zohra-publisher
   cp .env.example .env.production
   chmod 600 .env.production
   # Edit .env.production with production secrets
   ```
3. **Run Safe Deployment**:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/deploy.sh
   ```
4. **Create Super Admin Operator**:
   ```bash
   docker compose -f docker-compose.prod.yml exec api python -c "
   import asyncio
   from app.db.session import async_session_factory
   from app.db.models.operations import User, UserRole
   from app.core.security import hash_password

   async def create_admin():
       async with async_session_factory() as session:
           admin = User(
               username='superadmin',
               email='admin@yourdomain.com',
               hashed_password=hash_password('ChangeMeImmediately123!'),
               role=UserRole.SUPER_ADMIN.value,
               is_active=True
           )
           session.add(admin)
           await session.commit()
           print('✓ Superadmin user created.')

   asyncio.run(create_admin())
   "
   ```
5. **Open Command Center**:
   Navigate to `https://your-domain.com/console` (or `https://your-domain.com/` through Next.js) and log in.

---

## 3. Autonomy Activation Stages (Prompt #308)

Do NOT enable full autonomy immediately. Follow the progressive safety progression:

1. **Stage A: Dry Run**:
   - `AUTONOMY_ENABLED=false`
   - Test WordPress connection and Search Console property verification.
   - Run pipeline in dry run mode to inspect topics, evidence graph, and draft quality without public publishing.
2. **Stage B: Research Only**:
   - `autonomy_mode: RESEARCH_ONLY`
   - System autonomously discovers topics and builds research evidence packages.
3. **Stage C: Draft Only**:
   - `autonomy_mode: DRAFT_ONLY`
   - System drafts articles and runs full claim verification audits, holding approved drafts in draft status.
4. **Stage D: Auto Low Risk**:
   - `autonomy_mode: AUTO_LOW_RISK`
   - Articles with 100% claim verification, zero disputed facts, high editorial score (>85), and low risk category publish autonomously.
5. **Stage E: Policy Controlled**:
   - Full autonomous publishing active, strictly bounded by budget governor limits and per-site risk policies.
