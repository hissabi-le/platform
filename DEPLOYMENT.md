# Hissabi Platform Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Domain name pointing to your server
- SSL certificates (Let's Encrypt recommended)
- Environment variables configured

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database
POSTGRES_USER=hissabi_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=hissabi_prod

# Security
SECRET=<random-secret-key>
JWT_SECRET=<random-jwt-secret>

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Environment
ENVIRONMENT=production
```

**IMPORTANT**: Never commit the `.env` file to git. It's already in `.gitignore`.

## Production Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/hissabi-le/platform.git
cd platform
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your production values
```

### 3. Run Database Migrations

```bash
cd backend/api
docker-compose -f ../../docker-compose.prod.yml run --rm api .venv/bin/alembic upgrade head
cd ../..
```

### 4. Start Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Verify Services

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f api

# Check health
curl http://localhost:8000/health
```

## Frontend Deployment

### Option 1: Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variables:
   - `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
4. Deploy

### Option 2: Docker + Nginx

```bash
cd web-app
pnpm build
pnpm start
```

Configure Nginx to proxy:
- Frontend: Port 3000
- Backend API: Port 8000

## SSL/TLS Configuration

Use Certbot for Let's Encrypt:

```bash
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
```

### Database Backup

```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U hissabi_user hissabi_prod > backup.sql
```

## Scaling

To scale the API service:

```bash
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## Troubleshooting

### Database Connection Issues

```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Connect to database
docker-compose -f docker-compose.prod.yml exec db psql -U hissabi_user -d hissabi_prod
```

### CORS Errors

Ensure `CORS_ORIGINS` environment variable includes your frontend URL:

```bash
CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
```

### Migration Errors

```bash
# Check current migration status
docker-compose -f docker-compose.prod.yml run --rm api .venv/bin/alembic current

# View migration history
docker-compose -f docker-compose.prod.yml run --rm api .venv/bin/alembic history
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Set strong `SECRET` and `JWT_SECRET`
- [ ] Configure firewall (only ports 80, 443, 22 open)
- [ ] Enable SSL/TLS
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated

## Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm api .venv/bin/alembic upgrade head
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/hissabi-le/platform/issues
- Documentation: See `README.md` and `AGENTS.md`
