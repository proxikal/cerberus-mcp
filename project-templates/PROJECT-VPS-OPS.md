# {{PROJECT_NAME}} - VPS OPERATIONS

**Module Type:** On-Demand (load when doing VPS/deployment work)
**Core Reference:** See {{PROJECT_NAME}}.md for Critical Rules
**Purpose:** VPS command reference and deployment workflows

**Note:** This file is OPTIONAL - skip if your project doesn't use VPS/remote servers.

---

## VPS CONFIGURATION

```
VPS_USER:   {{VPS_USER}}
VPS_HOST:   {{VPS_HOST}}
VPS_DIR:    {{VPS_DIR}}
VPS_DOMAIN: {{VPS_DOMAIN}}
LOCAL_DIR:  {{LOCAL_DIR}}
```

---

## DEPLOYMENT WORKFLOW

### Standard Deployment (5 Steps)

```bash
# 1. Edit locally
# Work on files at {{LOCAL_DIR}}

# 2. Test locally
{{TEST_COMMAND}}

# 3. Commit
git add . && git commit -m "Description"

# 4. Deploy to VPS
rsync -avz --delete -e ssh {{SYNC_SOURCE}}/ {{VPS_USER}}@{{VPS_HOST}}:{{VPS_DIR}}/{{SYNC_SOURCE}}/
# Example: rsync -avz --delete -e ssh src/ deploy@1.2.3.4:/var/www/myapp/src/

# 5. Build and restart on VPS
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && {{BUILD_COMMAND}} && {{RESTART_COMMAND}}"
# Example: ssh deploy@1.2.3.4 "cd /var/www/myapp && npm run build && pm2 restart myapp"
```

### Quick Deploy (One-Liner)

```bash
rsync -avz --delete -e ssh {{SYNC_SOURCE}}/ {{VPS_USER}}@{{VPS_HOST}}:{{VPS_DIR}}/{{SYNC_SOURCE}}/ && \
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && {{BUILD_COMMAND}} && {{RESTART_COMMAND}}"
```

---

## CRITICAL DEPLOYMENT RULES

**NEVER SYNC THESE TO VPS:**
- Documentation: *.md files (except README.md if needed)
- Credentials: .env, credentials.json, keys
- Dev files: .DS_Store, *.log, node_modules
- [Add your exclusions]

**ALWAYS:**
- Edit locally at {{LOCAL_DIR}}
- Commit before deploying
- Test before deploying
- Verify after deploying

**NEVER:**
- Edit files directly on VPS
- Skip testing before deploy
- Deploy without committing
- Use root account (unless emergency)

---

## VPS OPERATIONS

### Check Service Status

```bash
# [CUSTOMIZE FOR YOUR STACK]

# Example: PM2 (Node.js)
ssh {{VPS_USER}}@{{VPS_HOST}} "pm2 list"

# Example: Systemd
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo systemctl status {{SERVICE_NAME}}"

# Example: Docker
ssh {{VPS_USER}}@{{VPS_HOST}} "docker ps"
```

### View Logs

```bash
# [CUSTOMIZE FOR YOUR STACK]

# Example: PM2
ssh {{VPS_USER}}@{{VPS_HOST}} "pm2 logs {{APP_NAME}} --lines 50"

# Example: Systemd
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo journalctl -u {{SERVICE_NAME}} -f"

# Example: Docker
ssh {{VPS_USER}}@{{VPS_HOST}} "docker logs {{CONTAINER_NAME}} --tail 50 --follow"

# Example: Direct log files
ssh {{VPS_USER}}@{{VPS_HOST}} "tail -f {{VPS_DIR}}/logs/app.log"
```

### Restart Services

```bash
# [CUSTOMIZE FOR YOUR STACK]

# Example: PM2
ssh {{VPS_USER}}@{{VPS_HOST}} "pm2 restart {{APP_NAME}}"

# Example: Systemd
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo systemctl restart {{SERVICE_NAME}}"

# Example: Docker
ssh {{VPS_USER}}@{{VPS_HOST}} "docker restart {{CONTAINER_NAME}}"
```

### Build Application

```bash
# [CUSTOMIZE FOR YOUR STACK]

# Example: Node.js
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && npm install && npm run build"

# Example: Python
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && pip install -r requirements.txt"

# Example: Go
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && go build -o bin/app"

# Example: Rust
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && cargo build --release"
```

### Check Deployed Files

```bash
# List files in VPS directory
ssh {{VPS_USER}}@{{VPS_HOST}} "ls -la {{VPS_DIR}}"

# Find specific files
ssh {{VPS_USER}}@{{VPS_HOST}} "find {{VPS_DIR}} -name '*.js' -type f | sort"

# Compare local vs VPS file count
diff <(find {{LOCAL_DIR}}/{{SYNC_SOURCE}} -name '*.js' | wc -l) \
     <(ssh {{VPS_USER}}@{{VPS_HOST}} "find {{VPS_DIR}}/{{SYNC_SOURCE}} -name '*.js' | wc -l")
```

---

## SYSTEM ADMINISTRATION

### Install Packages

```bash
# [CUSTOMIZE FOR YOUR VPS OS]

# Example: Ubuntu/Debian
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo apt-get update && sudo apt-get install -y {{PACKAGE}}"

# Example: CentOS/RHEL
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo yum install -y {{PACKAGE}}"

# Example: Arch
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo pacman -S {{PACKAGE}}"
```

### Firewall Management

```bash
# [CUSTOMIZE FOR YOUR FIREWALL]

# Example: UFW (Ubuntu)
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo ufw allow {{PORT}} && sudo ufw reload"
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo ufw status"

# Example: firewalld (CentOS)
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo firewall-cmd --add-port={{PORT}}/tcp --permanent && sudo firewall-cmd --reload"

# Example: iptables
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo iptables -A INPUT -p tcp --dport {{PORT}} -j ACCEPT"
```

### Disk Usage

```bash
# Check disk space
ssh {{VPS_USER}}@{{VPS_HOST}} "df -h"

# Check directory sizes
ssh {{VPS_USER}}@{{VPS_HOST}} "du -sh {{VPS_DIR}}/*"

# Find large files
ssh {{VPS_USER}}@{{VPS_HOST}} "find {{VPS_DIR}} -type f -size +100M -exec ls -lh {} \;"
```

### Process Management

```bash
# Check running processes
ssh {{VPS_USER}}@{{VPS_HOST}} "ps aux | grep {{APP_NAME}}"

# Kill process by PID
ssh {{VPS_USER}}@{{VPS_HOST}} "kill -9 {{PID}}"

# Check resource usage
ssh {{VPS_USER}}@{{VPS_HOST}} "top -b -n 1 | head -20"
```

---

## TROUBLESHOOTING

### Service Won't Start

```bash
# 1. Check logs for errors
ssh {{VPS_USER}}@{{VPS_HOST}} "{{LOG_COMMAND}}"

# 2. Check if port is already in use
ssh {{VPS_USER}}@{{VPS_HOST}} "sudo lsof -i :{{PORT}}"

# 3. Check file permissions
ssh {{VPS_USER}}@{{VPS_HOST}} "ls -la {{VPS_DIR}}"

# 4. Try starting manually
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && {{START_COMMAND}}"
```

### Build Fails

```bash
# 1. Check build logs
ssh {{VPS_USER}}@{{VPS_HOST}} "{{LOG_COMMAND}}"

# 2. Clear build cache
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && rm -rf {{CACHE_DIR}}"

# 3. Reinstall dependencies
ssh {{VPS_USER}}@{{VPS_HOST}} "cd {{VPS_DIR}} && {{INSTALL_COMMAND}}"

# 4. Check disk space
ssh {{VPS_USER}}@{{VPS_HOST}} "df -h"
```

### Files Not Syncing

```bash
# 1. Verify rsync completed successfully (check exit code)
echo $?  # Should be 0

# 2. Check file counts match
find {{LOCAL_DIR}}/{{SYNC_SOURCE}} -type f | wc -l
ssh {{VPS_USER}}@{{VPS_HOST}} "find {{VPS_DIR}}/{{SYNC_SOURCE}} -type f | wc -l"

# 3. Check specific file exists on VPS
ssh {{VPS_USER}}@{{VPS_HOST}} "ls -la {{VPS_DIR}}/{{FILE_PATH}}"

# 4. Re-run rsync with verbose output
rsync -avz --delete -e ssh --progress {{SYNC_SOURCE}}/ {{VPS_USER}}@{{VPS_HOST}}:{{VPS_DIR}}/{{SYNC_SOURCE}}/
```

---

## BACKUP & RECOVERY

### Create Backup

```bash
# [CUSTOMIZE FOR YOUR BACKUP STRATEGY]

# Example: Database backup
ssh {{VPS_USER}}@{{VPS_HOST}} "pg_dump {{DB_NAME}} > /tmp/backup-$(date +%Y%m%d).sql"

# Example: Files backup
ssh {{VPS_USER}}@{{VPS_HOST}} "tar -czf /tmp/backup-$(date +%Y%m%d).tar.gz {{VPS_DIR}}"

# Download backup to local
scp {{VPS_USER}}@{{VPS_HOST}}:/tmp/backup-*.tar.gz ~/backups/
```

### Restore from Backup

```bash
# [CUSTOMIZE FOR YOUR RESTORE PROCESS]

# Example: Database restore
scp ~/backups/backup-20260111.sql {{VPS_USER}}@{{VPS_HOST}}:/tmp/
ssh {{VPS_USER}}@{{VPS_HOST}} "psql {{DB_NAME}} < /tmp/backup-20260111.sql"

# Example: Files restore
scp ~/backups/backup-20260111.tar.gz {{VPS_USER}}@{{VPS_HOST}}:/tmp/
ssh {{VPS_USER}}@{{VPS_HOST}} "tar -xzf /tmp/backup-20260111.tar.gz -C {{VPS_DIR}}"
```

---

## HEALTH CHECKS

### Application Health

```bash
# [CUSTOMIZE FOR YOUR APP]

# Example: HTTP endpoint
curl {{VPS_DOMAIN}}/health
# Expected: {"status":"ok"}

# Example: TCP port check
nc -zv {{VPS_HOST}} {{PORT}}

# Example: Custom health check script
ssh {{VPS_USER}}@{{VPS_HOST}} "{{VPS_DIR}}/scripts/health-check.sh"
```

### System Health

```bash
# CPU usage
ssh {{VPS_USER}}@{{VPS_HOST}} "top -b -n 1 | head -5"

# Memory usage
ssh {{VPS_USER}}@{{VPS_HOST}} "free -h"

# Disk usage
ssh {{VPS_USER}}@{{VPS_HOST}} "df -h"

# Network connectivity
ssh {{VPS_USER}}@{{VPS_HOST}} "ping -c 3 8.8.8.8"
```

---

## ACCOUNTS & PERMISSIONS

**VPS Accounts:**
- Primary: `{{VPS_USER}}@{{VPS_HOST}}`
- [Add other accounts if applicable]

**Account Usage:**
- Use `{{VPS_USER}}` for: All VPS operations
- [Add rules for other accounts]

**Sudo Permissions:**
- [Document what {{VPS_USER}} can/cannot do with sudo]
- Never use `sudo` for: [operations that don't need it]

---

**Template Version:** 1.0 (2026-01-11)
**Origin:** XCalibr CLAUDE-VPS-OPS.md
**Customize:** Replace all {{PLACEHOLDERS}} and add project-specific commands
