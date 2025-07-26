
# 🎮 Tapis Vert

[![Game Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()
[![Deployment](https://img.shields.io/badge/deploy-terraform-purple.svg)]()

> **An online implementation of the classic Top 10 party game for groups of friends**

Tapis Vert brings the beloved **Top 10** party game to the web with real-time multiplayer features. Players receive secret numbered cards (1-10) and give creative answers that match their card's position on themed scales. The master tries to guess who has which number in this hilarious game of creativity and deduction!

## 🚀 **Quick Start**

### 🎮 **Want to Play?**
1. Get a room link from a friend or create your own room
2. Visit the link in your browser - you'll get a visitor ID automatically
3. Wait for the master to start a new round and receive your secret card
4. Give creative answers that match your card number!
5. See **[How to Play Guide](docs/user/README.md)** for complete instructions

### 💻 **Want to Deploy Your Own?**
```bash
# Quick deployment (requires config setup)
cd box/ && alias box=./box.sh
box terraform plan && box terraform apply
box deploy
box ssh "cd services && docker compose up -d"
```
See **[Infrastructure Guide](docs/dev-ops/infrastructure.md)** for complete setup.

## 📖 **Documentation**

| Audience | Documentation | Purpose |
|----------|---------------|---------|
| 🎮 **Players** | **[How to Play](docs/user/)** | Game rules, tips, getting started |
| 💻 **Developers/DevOps** | **[Technical Docs](docs/dev-ops/)** | APIs, architecture, deployment |
| 🛠️ **Administrators** | **[Admin Guide](docs/admin/)** | User/room management, debugging |
| ❓ **Everyone** | **[Game Rules](docs/game-rules.md)** | Complete Top 10 mechanics |

**📂 [Complete Documentation Index](docs/)** - Full overview of all documentation

## ✨ **Features**

- **🌐 Real-time Multiplayer**: Live game state synchronization via WebSockets
- **🎯 Role-based Access**: Players, masters, watchers, and visitors
- **📱 Cross-platform**: Works on desktop and mobile browsers
- **🔐 Passwordless Auth**: Magic link authentication system
- **💬 Live Chat**: Real-time messaging during games
- **🃏 Card Management**: Flip, peek, and reveal card mechanics
- **📊 Game Analytics**: Integrated monitoring and analytics
- **🚀 Cloud-native**: Containerized deployment on OpenStack

## 🏗️ **Architecture**

- **Backend**: Unified Flask app (public + admin blueprints) + FastAPI (WebSocket) + Redis (data & pub/sub)
- **Frontend**: Vanilla JavaScript with custom component system
- **Security**: Nginx-based admin route blocking with SSH tunnel access
- **Infrastructure**: Terraform on OpenStack with automated deployment
- **Monitoring**: Datadog APM + RUM, Mixpanel analytics

## 🎯 **Game Example**

**Theme**: *"On a scale from 1 (most boring) to 10 (most exciting), give me weekend activities"*

- **Card 2**: "Organizing my sock drawer"
- **Card 7**: "Skydiving" 
- **Card 10**: "Swimming with sharks while juggling flaming torches"

The master then tries to guess who has which card! 🤔

## 📋 **API Examples**

### For Developers/Admins
```bash
# Public API - Game management
curl -X POST "https://tapisvert.pcariou.fr/api/v1/rooms/abcd-1234/round"

# Authentication API
curl -X GET "https://tapisvert.pcariou.fr/api/auth/me"

# Access room as user (for testing)
https://tapisvert.pcariou.fr/r/abcd-1234?user=pierre

# Admin functions (SSH tunnel required)
# box -p 8000 admin tunnel, then visit http://localhost:8000/admin/list
# See docs/admin/ for complete admin documentation
```

See **[API Reference](docs/dev-ops/api-reference.md)** for complete documentation.

## 🔗 **Links**

- **🎮 [Live Demo](https://tapisvert.pcariou.fr/)** - Try the game!
- **📚 [Complete Documentation](docs/)** - All guides and references
- **🐛 [Report Issues](issues)** - Bug reports and feedback

---

*Ready to play? Get a group together and start having fun with Top 10! 🎉*
