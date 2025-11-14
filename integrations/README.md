# Soleflip Integrations

This directory contains optional integrations and extensions for the Soleflip platform.

## Available Integrations

### 🧠 Memori MCP Server

**Status**: ✅ Production Ready
**Location**: `memori-mcp/`
**Purpose**: AI Memory Engine via Model Context Protocol

Provides persistent memory capabilities for AI agents, LLMs, and multi-agent systems.

**Key Features:**
- Persistent memory across sessions
- Semantic search capabilities
- Context injection for AI agents
- Multi-namespace organization
- MCP-compatible (n8n, Claude Code)

**Documentation:**
- Quick Start: [memori-mcp/README.md](memori-mcp/README.md)
- Portainer Deployment: [../docs/integrations/portainer-memori-deployment.md](../docs/integrations/portainer-memori-deployment.md)
- Full Setup Guide: [../docs/integrations/memori-mcp-setup.md](../docs/integrations/memori-mcp-setup.md)

**Activation:**
```bash
# Portainer
Add Environment Variable: COMPOSE_PROFILES=memori

# Docker Compose CLI
docker-compose --profile memori up -d
```

## Integration Guidelines

### Adding New Integrations

When adding a new integration to this directory:

1. **Directory Structure**:
   ```
   integrations/
   └── your-integration/
       ├── Dockerfile          # Container definition
       ├── requirements.txt    # Dependencies
       ├── README.md          # Quick start guide
       ├── config.py          # Configuration
       └── ...                # Implementation files
   ```

2. **Docker Compose Integration**:
   - Add service to `docker-compose.yml`
   - Use `profiles:` for optional services
   - Follow resource limit patterns
   - Include health checks

3. **Documentation**:
   - Create README in integration directory (quick start)
   - Add detailed guide in `docs/integrations/`
   - Include Portainer-specific instructions
   - Provide example use cases

4. **Configuration**:
   - Use environment variables for all config
   - Add defaults in Dockerfile
   - Document all variables in `.env.example`
   - Support both Portainer and CLI workflows

5. **Database Integration**:
   - Add database creation to `init-databases.sql`
   - Use existing PostgreSQL instance
   - Create dedicated database per integration
   - Grant appropriate permissions

### Best Practices

✅ **Do:**
- Make integrations optional (use profiles)
- Provide comprehensive documentation
- Include health checks
- Set resource limits
- Use structured logging
- Support environment-based configuration
- Test in Portainer environment

❌ **Don't:**
- Don't expose unnecessary ports
- Don't hardcode credentials
- Don't skip health checks
- Don't forget .gitignore entries
- Don't bypass existing infrastructure

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Soleflip Stack                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌─────────────────────────────┐   │
│  │  Core Stack  │    │  Optional Integrations      │   │
│  │              │    │                             │   │
│  │ • Soleflip   │    │ • Memori MCP Server         │   │
│  │ • PostgreSQL │◄───┤ • Future integrations...    │   │
│  │ • Redis      │    │                             │   │
│  │ • n8n        │◄───┤                             │   │
│  │ • Metabase   │    │                             │   │
│  └──────────────┘    └─────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Roadmap

Planned integrations:

- [ ] **Vector Database** (Qdrant/Weaviate) for embeddings
- [ ] **Observability Stack** (Prometheus/Grafana)
- [ ] **API Gateway** (Kong/Traefik) for advanced routing
- [ ] **Message Queue** (RabbitMQ/Kafka) for event streaming
- [ ] **Cache Warming Service** for performance

## Support

For integration-specific issues:
1. Check the integration's README
2. Review detailed documentation in `docs/integrations/`
3. Check Portainer logs: Containers → [integration] → Logs
4. Open issue with `[Integration: name]` tag

## Contributing

To contribute a new integration:
1. Follow the guidelines above
2. Test in both Portainer and CLI environments
3. Document thoroughly
4. Submit PR with integration tag
5. Include example use cases

## License

All integrations follow the Soleflip project license unless otherwise specified.
