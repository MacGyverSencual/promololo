# Promololo

Monitor de preços de placas de vídeo em lojas brasileiras, com alertas pelo Telegram e execução automatizada pelo GitHub Actions.

## O que o projeto faz

- Busca ofertas de **AMD RX 9060 XT 16 GB** e **NVIDIA RTX 5060 / RTX 5060 Ti 16 GB**.
- Consulta KaBuM!, TerabyteShop, Pichau, Patoloco, GKInfoStore, Guerra Digital, Amazon Brasil, Mercado Livre, Magazine Luiza e Promotech.
- Envia um alerta pelo Telegram quando encontra uma oferta válida por **R$ 3.400 ou menos**.
- Evita repetir o mesmo alerta por 24 horas, exceto quando o preço cai.
- Pode enviar um resumo após uma execução manual, a pedido pelo Telegram ou uma vez nas faixas das 09h e das 21h (horário UTC−3).

A coleta usa Playwright e depende da estrutura das páginas das lojas, que pode mudar com o tempo.

## Executar localmente

Requisitos: Python 3.11 e uma conta/bot do Telegram. O workflow também instala o navegador Chromium usado pelo Playwright.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

No Windows, ative o ambiente virtual com `.venv\Scripts\Activate.ps1` no PowerShell. Configure as variáveis de ambiente antes de iniciar o monitor:

```bash
export TELEGRAM_TOKEN="token-do-seu-bot"
export TELEGRAM_CHAT_ID="id-do-seu-chat"
python monitor_gpu.py
```

No PowerShell, configure-as com `$env:TELEGRAM_TOKEN="token-do-seu-bot"` e `$env:TELEGRAM_CHAT_ID="id-do-seu-chat"` antes de executar `python monitor_gpu.py`.

O navegador é iniciado com interface gráfica. Em um servidor Linux sem display, instale também o Xvfb e execute com `xvfb-run --auto-servernum python monitor_gpu.py`.

## Configurar o GitHub Actions

O workflow em [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml) roda a cada cinco minutos e também pode ser iniciado manualmente pela aba **Actions** (`workflow_dispatch`). Para habilitar os avisos:

1. Crie um bot no Telegram e obtenha o ID do chat que receberá as mensagens.
2. No repositório, abra **Settings → Secrets and variables → Actions** e adicione os secrets `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`.
3. Permita que o GitHub Actions grave no repositório. O workflow usa a permissão `contents: write` para atualizar o histórico de alertas.

Para pedir uma busca pelo Telegram, envie uma mensagem de texto (por exemplo, `/buscar`) no chat configurado. O pedido será processado na próxima execução do workflow.

## Configuração e histórico

Os principais limites e a lista de lojas ficam no início de [`monitor_gpu.py`](monitor_gpu.py):

- `PRECO_ALVO`: preço máximo para gerar um alerta (atualmente R$ 3.400).
- `PRECO_MINIMO_SANIDADE`: ignora valores abaixo de R$ 1.500 para reduzir leituras inválidas.
- `HORAS_COOLDOWN_ALERTA`: intervalo padrão entre alertas iguais (atualmente 24 horas).
- `FONTES`: URLs de busca e páginas consultadas.

O arquivo [`alertas_enviados.json`](alertas_enviados.json) guarda os alertas recentes e o último update processado do Telegram. O GitHub Actions salva as alterações desse arquivo no repositório após cada execução; mantenha o histórico para preservar a deduplicação entre execuções.
