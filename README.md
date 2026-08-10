# Portal de Monitoramento

Painel visual inspirado no portal LOBO-GUARÁ 2026, com:

- status HTTP dos serviços;
- tempo de resposta;
- estado dos contêineres Docker;
- CPU, memória, disco e uptime do host;
- atualização automática.

## Instalação

```bash
cd /opt
mkdir -p portal-monitoramento
cd portal-monitoramento
# copie os arquivos deste projeto
docker compose up -d --build
```

Acesso direto:

```text
http://IP_DO_SERVIDOR:3080
```

## Imagens

Coloque:

- `static/img/brasao.png`
- `static/img/fundo.jpg`

## Nginx Proxy Manager

Adicione uma Custom Location no Proxy Host existente:

```text
Location: /painel
Scheme: http
Forward Hostname/IP: portal-monitoramento
Forward Port: 8080
```

Advanced:

```nginx
rewrite ^/painel/?(.*)$ /$1 break;

proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Prefix /painel;

proxy_read_timeout 60;
proxy_send_timeout 60;
```

Na aba Advanced principal do Proxy Host:

```nginx
location = /painel {
    return 302 /painel/;
}
```
