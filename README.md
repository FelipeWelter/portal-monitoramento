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

Acesse o portal em `http://IP_DO_SERVIDOR:32773`. Para usar outra porta no
servidor, crie um arquivo `.env` ao lado de `docker-compose.yml` com a porta
desejada e rode `docker compose up -d --build` novamente.

```text
PORTAL_PORT=18080
```

Nesse exemplo, o endereço passa a ser `http://IP_DO_SERVIDOR:18080`. A porta
`8080` é usada apenas dentro do contêiner.

## Testes

```bash
docker compose ps
docker exec portal-monitoramento ping -c 2 10.133.212.11
docker exec portal-monitoramento ping -c 2 10.133.212.13
docker exec portal-monitoramento ping -c 2 10.166.66.198
curl http://127.0.0.1:32773/health
```

Se você definiu `PORTAL_PORT`, use essa porta no endereço de `/health`.
