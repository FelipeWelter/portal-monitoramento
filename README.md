# Portal de Monitoramento

Painel de monitoramento HTTP/HTTPS e ICMP (PING), com métricas do host e estado de contêineres Docker.

## Monitores PING incluídos

- 10.133.212.11 — Servidor de Arquivos
- 10.133.212.13 — C2 em Combate Interno
- 10.166.66.198 — C2 Combate 7º CTA

## Instalação

```bash
cd /opt/portal-monitoramento
docker compose up -d --build
```

Acesso direto na porta 80:

```text
http://IP_DO_SERVIDOR
```

## Testes

```bash
docker compose ps
docker exec portal-monitoramento ping -c 2 10.133.212.11
docker exec portal-monitoramento ping -c 2 10.133.212.13
docker exec portal-monitoramento ping -c 2 10.166.66.198
curl http://127.0.0.1/health
```
