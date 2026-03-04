# Deployment Guide for 1GB VPS

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   - Set strong `POSTGRES_PASSWORD`
   - Set `JWT_SECRET_KEY` (min 32 chars)
   - Add your LLM API keys

3. **Build and start:**
   ```bash
   docker-compose up -d --build
   ```

4. **Run database migrations:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Access:**
   - Frontend: http://your-server-ip:3000
   - Backend API: http://your-server-ip:8000
   - API Docs: http://your-server-ip:8000/docs

## Resource Usage (1GB VPS)

| Service | Memory Limit |
|---------|--------------|
| Postgres | 256M |
| Backend | 512M |
| Frontend | 256M |
| **Total** | ~1GB |

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Update code and rebuild
git pull
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
```

## Production Tips

1. **Use nginx as reverse proxy** (terminates SSL, serves static files)
2. **Set `DEBUG=false`** in environment
3. **Regular database backups:**
   ```bash
   docker-compose exec postgres pg_dump -U postgres todoagent > backup.sql
   ```
4. **Monitor resources:**
   ```bash
   docker stats
   ```
