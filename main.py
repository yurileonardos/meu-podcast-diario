import os
import feedparser
import google.generativeai as genai
import asyncio
import edge_tts
from datetime import datetime
import pytz

# --- CONFIGURAÇÕES DO USUÁRIO ---
GITHUB_USER = "yurileonardos"  # <--- TROQUE PELO SEU USUÁRIO DO GITHUB AQUI
REPO_NAME = "meu-podcast-diario"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# --- FONTES SELECIONADAS (Curadoria Completa) ---
FEEDS = {
    "LOCAL (GOIÂNIA E GOIÁS)": [
        "https://g1.globo.com/rss/g1/goias/",            # G1 Goiás (Principal)
        "https://www.jornalopcao.com.br/feed/",           # Jornal Opção (Política Local)
        "https://www.maisgoias.com.br/feed/",             # Mais Goiás (Cotidiano)
        "https://agenciabrasil.ebc.com.br/rss/regioes/centro-oeste" # EBC Centro-Oeste
    ],
    "BRASIL (POLÍTICA E ECONOMIA)": [
        "https://www.brasil247.com/feed",                 # Brasil 247
        "https://cartacapital.com.br/feed/",              # Carta Capital
        "https://www.metropoles.com/feed",                # Metrópoles (Bastidores BSB)
        "https://agenciabrasil.ebc.com.br/rss/ultimas-noticias/feed.xml", # Oficial
        "https://super.abril.com.br/feed/",               # Superinteressante (Ciência/Curiosidades)
        "https://feeds.folha.uol.com.br/poder/rss091.xml" # Folha Poder
    ],
    "DESTAQUES YOUTUBE (ICL / DESMASCARANDO)": [
        # O RSS do YouTube traz o título e a descrição dos vídeos recentes
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCO6j6cqBhi2TWVxfcn6t23w", # Desmascarando
        "https://www.youtube.com/feeds/videos.xml?channel_id=UC6w8cK5C5QZJ9J9J9J9J9J9", # ICL Notícias
    ],
    "MUNDO (INTERNACIONAL)": [
        "https://brasil.elpais.com/rss/elpais/america.xml", # El País
        "https://www.bbc.com/portuguese/index.xml",         # BBC Brasil
        "https://rss.dw.com/xml/rss-br-all",                # Deutsche Welle
    ]
}

# --- 1. COLETOR ROBUSTO ---
def get_news_summary():
    texto_final = ""
    print("Coletando notícias de todas as fontes...")
    
    for categoria, urls in FEEDS.items():
        texto_final += f"\n--- {categoria} ---\n"
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # Pega até 5 notícias de cada fonte para garantir profundidade
                for entry in feed.entries[:5]:
                    title = entry.title
                    # Tenta pegar o sumário ou content; se não tiver, pega vazio
                    summary = entry.summary if 'summary' in entry else ""
                    # Limpa HTML básico do sumário para economizar tokens
                    summary = summary.replace("<p>", "").replace("</p>", "").replace("<strong>", "")[:300]
                    
                    source_name = entry.get('source', {}).get('title', 'Fonte')
                    texto_final += f"Fonte: {source_name} | Título: {title} | Resumo: {summary}\n"
            except Exception as e:
                continue # Se uma fonte falhar, segue para a próxima
    return texto_final

# --- 2. CÉREBRO JORNALÍSTICO (GEMINI) ---
def make_script(news_text):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido e capaz
    
    data_hoje = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d de %B de %Y')
    dia_semana = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%A')
    
    # Prompt projetado para profundidade e completude
    prompt = f"""
    Você é o âncora de um podcast jornalístico diário de alta credibilidade focado em Goiás e no Brasil.
    Data: {dia_semana}, {data_hoje}.
    
    Seu objetivo é criar um roteiro COMPLETO e DETALHADO. O ouvinte quer profundidade, não apenas manchetes rápidas.
    
    MATÉRIA PRIMA (Notícias coletadas):
    {news_text}
    
    ESTRUTURA OBRIGATÓRIA DO ROTEIRO:
    
    1. ABERTURA: 
       - Cumprimente o ouvinte ("Bom dia, Goiânia, bom dia, Goiás...").
       - Cite a data e faça uma prévia rápida (Headlines) dos 3 maiores assuntos do dia.

    2. BLOCO LOCAL (GOIÁS E GOIÂNIA) - [Dê prioridade a este bloco]:
       - Analise as notícias de Goiânia e do Governo de Goiás.
       - Trânsito, obras, política local (Paço Municipal/Governo Estadual), clima ou crimes de repercussão.
       - Se houver notícias do Jornal Opção ou G1 Goiás, detalhe-as.

    3. BLOCO BRASIL (POLÍTICA E ECONOMIA):
       - Sintetize as grandes movimentações em Brasília.
       - Use as informações do Brasil 247, ICL e Carta Capital para dar o tom político.
       - Inclua decisões econômicas que afetam o bolso do cidadão.
       - Se houver novidades nos canais "Desmascarando" ou "ICL", mencione como "Destaques das redes".

    4. BLOCO MUNDO:
       - Resumo consistente dos principais conflitos ou decisões globais (EUA, Europa, China) baseados na BBC/DW.

    5. ENCERRAMENTO:
       - Uma despedida cordial.
    
    TOM DE VOZ:
    - Sério, porém conversado.
    - Use conectivos ("Por outro lado", "Enquanto isso em Brasília", "Voltando para Goiás").
    - NÃO use colchetes de instrução no texto final (ex: [Música sobe]). Escreva apenas o texto falado.
    - Texto longo é permitido para garantir a completude.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "Desculpe, tivemos um problema técnico ao processar as notícias de hoje. Voltamos amanhã."

# --- 3. GERADOR DE ÁUDIO ---
async def gen_audio(text, filename):
    # Voz Masculina Jornalística (Antonio) ou Feminina (Francisca). 
    # Antonio soa mais formal para notícias completas.
    communicate = edge_tts.Communicate(text, "pt-BR-AntonioNeural") 
    await communicate.save(filename)

# --- 4. PUBLICADOR RSS ---
def update_rss(audio_filename, title):
    rss_file = "feed.xml"
    audio_url = f"{BASE_URL}/{audio_filename}"
    now = datetime.now(pytz.timezone('America/Sao_Paulo'))
    
    # Item do episódio
    rss_item = f"""
    <item>
      <title>{title}</title>
      <description>Notícias completas de Goiás, Brasil e Mundo. Fontes: G1, ICL, 247, Opção e mais.</description>
      <enclosure url="{audio_url}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
    </item>
    """
    
    # Cria ou atualiza o arquivo XML
    if not os.path.exists(rss_file):
        with open(rss_file, 'w', encoding='utf-8') as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Goiás & Brasil Diário</title>
    <description>Resumo diário aprofundado de notícias locais, nacionais e internacionais.</description>
    <link>{BASE_URL}</link>
    <language>pt-br</language>
    <itunes:image href="https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/640px-Flag_of_Brazil.svg.png"/>
    {rss_item}
  </channel>
</rss>""")
    else:
        with open(rss_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Insere o novo episódio no topo da lista
        tag_alvo = "</language>"
        if tag_alvo in content:
             # Se tiver imagem, insere depois da imagem, senão depois da language
            pos = content.find(tag_alvo) + len(tag_alvo)
            # Ajuste fino para não quebrar XML se tiver tags extras
            if "<itunes:image" in content:
                pos = content.find("/>", content.find("<itunes:image")) + 2
                
            new_content = content[:pos] + rss_item + content[pos:]
            with open(rss_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("--- Iniciando Robô de Notícias (Modo Completo) ---")
    
    # 1. Coletar
    news_content = get_news_summary()
    
    if len(news_content) > 200:
        print("Notícias coletadas. Escrevendo roteiro detalhado...")
        
        # 2. Escrever
        script = make_script(news_content)
        
        # Nome do arquivo com data
        hoje_str = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y%m%d')
        filename = f"podcast_completo_{hoje_str}.mp3"
        
        print("Gravando áudio (isso pode levar um minuto)...")
        # 3. Gravar
        asyncio.run(gen_audio(script, filename))
        
        # 4. Publicar
        print("Atualizando Feed RSS...")
        display_date = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m')
        update_rss(filename, f"Edição Completa: {display_date}")
        
        print("✅ Podcast Publicado com Sucesso!")
    else:
        print("❌ Erro: Não foi possível coletar notícias suficientes.")
