import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import requests
from playwright.sync_api import sync_playwright

# ================= CONFIGURAÇÕES =================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PRECO_ALVO = 3400.00
PRECO_MINIMO_SANIDADE = 1500.00  # Ignora parcelas (ex: 10x R$ 400), caixas vazias e suportes
ARQUIVO_HISTORICO = "alertas_enviados.json"
HORAS_COOLDOWN_ALERTA = 24       # Não repete o mesmo alerta por 24h (a menos que o preço caia mais)

FONTES = [
    # Links diretos específicos (KaBuM!)
    {
        "loja": "KaBuM! (Link Direto)",
        "tipo": "kabum_produto",
        "base_url": "https://www.kabum.com.br",
        "url": "https://www.kabum.com.br/produto/870975"
    },
    # KaBuM! (Buscas gerais)
    {
        "loja": "KaBuM!",
        "tipo": "kabum",
        "base_url": "https://www.kabum.com.br",
        "url": "https://www.kabum.com.br/busca/rx-9060-xt"
    },
    {
        "loja": "KaBuM!",
        "tipo": "kabum",
        "base_url": "https://www.kabum.com.br",
        "url": "https://www.kabum.com.br/busca/rtx-5060-ti"
    },
    # TerabyteShop
    {
        "loja": "TerabyteShop",
        "tipo": "terabyte",
        "base_url": "https://www.terabyteshop.com.br",
        "url": "https://www.terabyteshop.com.br/busca?str=rx+9060+xt+16gb"
    },
    {
        "loja": "TerabyteShop",
        "tipo": "terabyte",
        "base_url": "https://www.terabyteshop.com.br",
        "url": "https://www.terabyteshop.com.br/busca?str=rtx+5060+ti+16gb"
    },
    # Pichau
    {
        "loja": "Pichau",
        "tipo": "pichau",
        "base_url": "https://www.pichau.com.br",
        "url": "https://www.pichau.com.br/search?q=rx%209060%20xt%2016gb"
    },
    {
        "loja": "Pichau",
        "tipo": "pichau",
        "base_url": "https://www.pichau.com.br",
        "url": "https://www.pichau.com.br/search?q=rtx%205060%20ti%2016gb"
    },
    # Patoloco
    {
        "loja": "Patoloco",
        "tipo": "generico_loja",
        "base_url": "https://patoloco.com.br",
        "url": "https://patoloco.com.br/busca?q=rx+9060+xt+16gb"
    },
    {
        "loja": "Patoloco",
        "tipo": "generico_loja",
        "base_url": "https://patoloco.com.br",
        "url": "https://patoloco.com.br/busca?q=rtx+5060+ti+16gb"
    },
    # GKInfoStore
    {
        "loja": "GKInfoStore",
        "tipo": "generico_loja",
        "base_url": "https://www.gkinfostore.com.br",
        "url": "https://www.gkinfostore.com.br/busca?q=rx+9060+xt+16gb"
    },
    {
        "loja": "GKInfoStore",
        "tipo": "generico_loja",
        "base_url": "https://www.gkinfostore.com.br",
        "url": "https://www.gkinfostore.com.br/busca?q=rtx+5060+ti+16gb"
    },
    # Guerra Digital
    {
        "loja": "Guerra Digital",
        "tipo": "generico_loja",
        "base_url": "https://www.guerradigital.com.br",
        "url": "https://www.guerradigital.com.br/busca?busca=rx+9060+xt+16gb"
    },
    {
        "loja": "Guerra Digital",
        "tipo": "generico_loja",
        "base_url": "https://www.guerradigital.com.br",
        "url": "https://www.guerradigital.com.br/busca?busca=rtx+5060+ti+16gb"
    },
    # Amazon Brasil
    {
        "loja": "Amazon Brasil",
        "tipo": "amazon",
        "base_url": "https://www.amazon.com.br",
        "url": "https://www.amazon.com.br/s?k=placa+de+video+rx+9060+xt+16gb"
    },
    {
        "loja": "Amazon Brasil",
        "tipo": "amazon",
        "base_url": "https://www.amazon.com.br",
        "url": "https://www.amazon.com.br/s?k=placa+de+video+rtx+5060+ti+16gb"
    },
    # Mercado Livre (somente anúncios nacionais)
    {
        "loja": "Mercado Livre",
        "tipo": "mercadolivre",
        "base_url": "https://lista.mercadolivre.com.br",
        "url": "https://lista.mercadolivre.com.br/placa-video-rx-9060-xt-16gb_NoIndex_True"
    },
    {
        "loja": "Mercado Livre",
        "tipo": "mercadolivre",
        "base_url": "https://lista.mercadolivre.com.br",
        "url": "https://lista.mercadolivre.com.br/placa-video-rtx-5060-ti-16gb_NoIndex_True"
    },
    # Magazine Luiza
    {
        "loja": "Magazine Luiza",
        "tipo": "magalu",
        "base_url": "https://www.magazineluiza.com.br",
        "url": "https://www.magazineluiza.com.br/busca/placa+de+video+rx+9060+xt+16gb/"
    },
    {
        "loja": "Magazine Luiza",
        "tipo": "magalu",
        "base_url": "https://www.magazineluiza.com.br",
        "url": "https://www.magazineluiza.com.br/busca/placa+de+video+rtx+5060+ti+16gb/"
    },
    # Promotech (Agregador brasileiro - backup para ofertas à vista)
    {
        "loja": "Promotech (Agregador BR)",
        "tipo": "promotech",
        "base_url": "https://promotech.app.br",
        "url": "https://promotech.app.br/produtos/placa-de-video/wr270nsn/rx-9060-xt-16gb"
    },
    {
        "loja": "Promotech (Agregador BR)",
        "tipo": "promotech",
        "base_url": "https://promotech.app.br",
        "url": "https://promotech.app.br/produtos/placa-de-video/ujh02rgi/rtx-5060-ti-16gb"
    },
]
# =================================================


def enviar_telegram(mensagem: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        if not resp.ok:
            print(f"Falha Telegram ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")


def verificar_comando_telegram(historico: dict) -> bool:
    """
    Verifica se você enviou alguma mensagem/comando (ex: /buscar) no chat do bot
    desde a última execução.
    """
    ultimo_id = historico.get("_ultimo_update_id", 0)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": ultimo_id + 1, "timeout": 5}, timeout=10)
        if not resp.ok:
            return False

        dados = resp.json()
        updates = dados.get("result", [])
        if not updates:
            return False

        maior_id = ultimo_id
        solicitou_busca = False

        for item in updates:
            upd_id = item.get("update_id", 0)
            if upd_id > maior_id:
                maior_id = upd_id

            msg = item.get("message") or item.get("edited_message") or {}
            chat_id = str(msg.get("chat", {}).get("id", ""))
            texto = (msg.get("text") or "").strip().lower()

            # Aceita apenas comandos vindos da sua própria conta do Telegram
            if chat_id == str(TELEGRAM_CHAT_ID) and texto:
                solicitou_busca = True

        historico["_ultimo_update_id"] = maior_id
        return solicitou_busca
    except Exception as e:
        print(f"Erro ao checar comandos no Telegram: {e}")
        return False


def carregar_historico() -> dict:
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salvar_historico(historico: dict):
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def limpar_preco(texto: str) -> float | None:
    """Extrai o menor valor à vista em R$ de um bloco de texto."""
    matches = re.findall(r"R\$\s*([\d\.]+,\d{2})", texto)
    valores = []
    for m in matches:
        try:
            val = float(m.replace(".", "").replace(",", "."))
            if val >= PRECO_MINIMO_SANIDADE:
                valores.append(val)
        except ValueError:
            continue
    return min(valores) if valores else None


def titulo_valido(titulo: str, texto_completo: str = "") -> str | None:
    """
    Valida se o anúncio é realmente uma RX 9060 XT 16GB ou RTX 5060 (Ti) 16GB,
    bloqueando PCs montados, notebooks, versões de 8GB e anúncios internacionais.
    """
    t = titulo.lower()
    t_card = texto_completo.lower()

    bloqueados_titulo = [
        "pc gamer", "computador", "notebook", "laptop", "ddr4", "ddr5",
        "ryzen", "core i", "ssd", "fonte", "caixa vazia", "defeito",
        "quebrada", "usada", "open box", "internacional", "importado", "china"
    ]
    if any(b in t for b in bloqueados_titulo):
        return None

    if "compra internacional" in t_card or "enviado da china" in t_card:
        return None

    if not re.search(r"\b16\s*gb\b", t):
        return None

    if re.search(r"\b9060\s*xt\b", t):
        return "AMD RX 9060 XT 16GB"
    if re.search(r"\b5060(\s*ti)?\b", t):
        return "NVIDIA RTX 5060 (Ti) 16GB"

    return None


def normalizar_link(href: str | None, base_url: str, fallback: str) -> str:
    if not href:
        return fallback
    return urljoin(base_url, href)


def coletar_ofertas(pagina, fonte: dict) -> list[dict]:
    ofertas = []
    tipo = fonte["tipo"]
    loja = fonte["loja"]
    base_url = fonte["base_url"]

    pagina.goto(fonte["url"], timeout=30000, wait_until="domcontentloaded")
    pagina.wait_for_timeout(2500)

    if tipo == "kabum_produto":
        titulo_el = pagina.locator("h1").first
        titulo = titulo_el.inner_text().strip() if titulo_el.count() else ""
        corpo_topo = pagina.locator("main").first.inner_text() if pagina.locator("main").count() else ""

        tem_botao_comprar = pagina.locator('button:has-text("COMPRAR"), button:has-text("Comprar")').count() > 0
        indisponivel = "produto indisponível" in corpo_topo.lower() or "avise-me quando chegar" in corpo_topo.lower()

        if titulo and tem_botao_comprar and not indisponivel:
            preco_el = pagina.locator('h4.finalPrice, [class*="finalPrice"]').first
            texto_preco = preco_el.inner_text().strip() if preco_el.count() else ""
            if texto_preco:
                ofertas.append({
                    "loja": loja,
                    "titulo": titulo,
                    "texto": texto_preco,
                    "url": fonte["url"],
                })

    elif tipo == "kabum":
        cards = pagina.locator("article.productCard")
        if cards.count() == 0:
            cards = pagina.locator("a[href*='/produto/']")
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            link_el = el if el.get_attribute("href") else el.locator("a[href*='/produto/']").first
            href = link_el.get_attribute("href") if link_el.count() else None
            titulo_el = el.locator("span.nameCard, h2, h3").first
            if titulo_el.count():
                titulo = titulo_el.inner_text().strip()
            else:
                linhas = [
                    l.strip() for l in texto.split("\n")
                    if len(l.strip()) > 15 and "R$" not in l and "%" not in l and "FRETE" not in l.upper()
                ]
                titulo = max(linhas, key=len) if linhas else ""
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "terabyte":
        cards = pagina.locator(".pbox, .commerce_columns_item_inner")
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            link_el = el.locator("a.prod-name, a[href*='/produto/']").first
            href = link_el.get_attribute("href") if link_el.count() else None
            titulo = link_el.inner_text().strip() if link_el.count() else texto.split("\n")[0]
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "pichau":
        cards = pagina.locator('a[data-cy="list-product"], a[href*="/placa-de-video-"]')
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            href = el.get_attribute("href")
            titulo_el = el.locator("h2, h3").first
            titulo = titulo_el.inner_text().strip() if titulo_el.count() else texto.split("\n")[0]
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "amazon":
        cards = pagina.locator('div[data-component-type="s-search-result"]')
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            link_el = el.locator('h2 a, a.a-link-normal[href*="/dp/"]').first
            href = link_el.get_attribute("href") if link_el.count() else None
            titulo_el = el.locator("h2").first
            titulo = titulo_el.inner_text().strip() if titulo_el.count() else texto.split("\n")[0]
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "mercadolivre":
        cards = pagina.locator("li.ui-search-layout__item, div.poly-card")
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            link_el = el.locator("a[href]").first
            href = link_el.get_attribute("href") if link_el.count() else None
            titulo_el = el.locator("h2, h3, .poly-component__title").first
            titulo = titulo_el.inner_text().strip() if titulo_el.count() else texto.split("\n")[0]
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "magalu":
        cards = pagina.locator('a[data-testid="product-card-container"]')
        total = min(cards.count(), 25)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            href = el.get_attribute("href")
            titulo_el = el.locator('[data-testid="product-title"]').first
            titulo = titulo_el.inner_text().strip() if titulo_el.count() else texto.split("\n")[0]
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "promotech":
        cards = pagina.locator('a[href*="/produtos/placa-de-video/modelo/"]')
        total = cards.count()
        for i in range(total):
            el = cards.nth(i)
            container = el.locator("xpath=ancestor::div[2]")
            texto = container.inner_text()
            titulo = el.inner_text().strip() or texto.split("\n")[0]
            href = el.get_attribute("href")
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    elif tipo == "generico_loja":
        cards = pagina.locator(
            ".product-item, .card-product, .listagem-item, .product-card, "
            "a[href*='/produto/'], a[href*='/placa-de-video']"
        )
        total = min(cards.count(), 30)
        for i in range(total):
            el = cards.nth(i)
            texto = el.inner_text()
            if "R$" not in texto:
                pai = el.locator("xpath=ancestor::div[2]")
                if pai.count():
                    texto = pai.inner_text()
            link_el = el if el.get_attribute("href") else el.locator("a[href]").first
            href = link_el.get_attribute("href") if link_el.count() else None
            linhas = [l.strip() for l in texto.split("\n") if len(l.strip()) > 12 and "R$" not in l]
            titulo = linhas[0] if linhas else ""
            ofertas.append({
                "loja": loja,
                "titulo": titulo,
                "texto": texto,
                "url": normalizar_link(href, base_url, fonte["url"]),
            })

    return ofertas


def executar_monitoramento():
    historico = carregar_historico()
    agora = datetime.now(timezone(timedelta(hours=-3)))
    execucao_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    pedido_telegram = verificar_comando_telegram(historico)

    if pedido_telegram:
        enviar_telegram("🔎 <b>Pedido recebido!</b> Varrendo as lojas agora, aguarde ~1 minuto...")

    melhores_precos = {}
    novos_alertas = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        contexto = navegador.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        contexto.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        pagina = contexto.new_page()

        for fonte in FONTES:
            try:
                brutos = coletar_ofertas(pagina, fonte)
                for item in brutos:
                    categoria = titulo_valido(item["titulo"], item["texto"])
                    if not categoria:
                        continue

                    preco = limpar_preco(item["texto"])
                    if not preco:
                        continue

                    if categoria not in melhores_precos or preco < melhores_precos[categoria]["preco"]:
                        melhores_precos[categoria] = {
                            "preco": preco,
                            "titulo": item["titulo"][:90],
                            "loja": item["loja"],
                            "url": item["url"],
                        }

                    if preco <= PRECO_ALVO:
                        chave_id = hashlib.md5(
                            f"{item['loja']}|{item['titulo'][:50]}".encode()
                        ).hexdigest()[:12]

                        registro = historico.get(chave_id)
                        deve_alertar = True
                        if registro:
                            ultimo_envio = datetime.fromisoformat(registro["data"])
                            ultimo_preco = registro["preco"]
                            if (agora - ultimo_envio) < timedelta(hours=HORAS_COOLDOWN_ALERTA) and preco >= ultimo_preco:
                                deve_alertar = False

                        if deve_alertar:
                            historico[chave_id] = {
                                "preco": preco,
                                "titulo": item["titulo"][:90],
                                "data": agora.isoformat(),
                            }
                            novos_alertas.append(
                                f"🚨 <b>PROMOLOLO — ALERTA DE PREÇO (≤ R$ {PRECO_ALVO:,.2f})!</b>\n"
                                f"🎮 <b>Modelo:</b> {categoria}\n"
                                f"📦 <b>Anúncio:</b> {item['titulo'][:90]}\n"
                                f"🏪 <b>Loja:</b> {item['loja']}\n"
                                f"💰 <b>Preço:</b> <b>R$ {preco:,.2f}</b>\n"
                                f"🔗 <a href='{item['url']}'>Abrir oferta</a>"
                            )

            except Exception as e:
                print(f"Aviso ao ler {fonte['loja']} ({fonte['url']}): {e}")

        navegador.close()

    # 1. Envia alertas imediatos sempre que alguma GPU atingir R$ 3.400,00 ou menos
    for alerta in novos_alertas:
        enviar_telegram(alerta)

    # 2. Envia o relatório completo se foi teste manual, pedido pelo Telegram (/buscar) ou resumo das 09h/21h
    chave_resumo = agora.strftime("%Y-%m-%d-%H")
    enviar_status_agendado = agora.hour in (9, 21) and historico.get("_ultimo_resumo") != chave_resumo

    if execucao_manual or pedido_telegram or enviar_status_agendado:
        if enviar_status_agendado:
            historico["_ultimo_resumo"] = chave_resumo

        if pedido_telegram:
            titulo_msg = "🔎 <b>Promololo — Resultado da sua busca sob demanda</b>"
        elif execucao_manual:
            titulo_msg = "✅ <b>Promololo — Teste concluído com sucesso!</b>"
        else:
            titulo_msg = f"📡 <b>Promololo — Status ({agora.strftime('%d/%m %H:%M')})</b>"

        linhas = [f"{titulo_msg}\n🎯 Alvo configurado: <b>R$ {PRECO_ALVO:,.2f}</b> ou menos\n"]
        if melhores_precos:
            for cat, info in melhores_precos.items():
                linhas.append(
                    f"• <b>{cat}</b>: menor encontrado agora <b>R$ {info['preco']:,.2f}</b> ({info['loja']})\n"
                    f"  <i>{info['titulo']}</i>\n"
                    f"  🔗 <a href='{info['url']}'>Ver oferta</a>"
                )
        else:
            linhas.append("Nenhuma placa em estoque foi lida nesta rodada.")
        enviar_telegram("\n".join(linhas))

    salvar_historico(historico)


if __name__ == "__main__":
    executar_monitoramento()
