import os
import feedparser
import google.generativeai as genai
import asyncio
import edge_tts
from datetime import datetime
import pytz
from xml.sax.saxutils import escape
import re

# --- CONFIGURAÇÕES DO USUÁRIO ---
GITHUB_USER = "yurileonardos"  # <--- SEU USUÁRIO AQUI
REPO_NAME = "meu-podcast-diario"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# --- FONTES (Curadoria Yuri: Vila & Cruzeiro) ---
FEEDS = {
    "GOIÁS (Política e Cotidiano)": [
        "https://g1.globo.com/rss/g1/goias/",
        "https://www.jornalopcao.com.br/feed/",
        "https://www.maisgoias.com.br/feed/"
    ],
    "ESPORTES (Vila Nova & Cruzeiro)": [
        "https://ge.globo.com/rss/ge/futebol/times/vila-nova/",   # VILA NOVA
        "https://ge.globo.com/rss/ge/futebol/times/cruzeiro/",    # CRUZEIRO
        "https://www.maisgoias.com.br/category/esportes/vila-nova/feed/"
    ],
    "BRASIL (Política, Justiça, Economia)": [
        "https://www.brasil247.com/feed",
        "https://cartacapital.com.br/feed/",
        "https://agenciabrasil.ebc.com.br/rss/ultimas-noticias/feed.xml",
        "https://feeds.folha.uol.com.br/poder/rss091.xml"
    ],
    "MUNDO (Todos os Continentes)": [
        "https://brasil.elpais.com/rss/elpais/america.xml",
        "https://www.bbc.com/portuguese/index.xml", 
        "https://rss.dw.com/xml/rss-br-all",        
        "https://news.un.org/feed/subscribe/pt/news/all/rss.xml" 
    ],
    "CIÊNCIA E TECNOLOGIA": [
        "https://super.abril.com.br/feed/",
        "https://gizmodo.uol.com.br/feed/",
    ]
}

def get_news_summary():
    texto_final = ""
    print("Coletando notícias...")
    for categoria, urls in FEEDS.items():
        texto_final += f"\n--- {categoria} ---\n"
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # Pega até 4 notícias de cada para ter variedade
                for entry in feed.entries[:4]:
                    title = entry.title
                    summary = entry.summary if 'summary' in entry else ""
                    summary = re.sub(r'<[^>]+>', '', summary)[:300]
                    texto_final += f"- {title}: {summary}\n"
            except: continue
    return texto_final

def clean_text_for_speech(text):
    text = text.replace("*", "")
    text = text.replace("#", "")
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'http\S+', '', text)
    text = text.replace("BRL", "reais")
    return text

def make_script(news_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    # Auto-seletor de modelo
    model_name = 'gemini-pro'
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    model_name = m.name
                    break
    except: pass

    try:
        model = genai.GenerativeModel(model_name)
        data_hoje = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d de %B')
        
        # --- PROMPT PERSONALIZADO: YURI, VILA & CRUZEIRO ---
        prompt = f"""
        Você é um podcaster inteligente e carismático gravando um áudio exclusivo para o ouvinte Yuri.
        Data de hoje: {data_hoje}.
        
        ESTRUTURA OBRIGATÓRIA:
        1. SAUDAÇÃO: Comece EXATAMENTE com: "Olá, seja bem-vindo Yuri ao nosso bate-papo diário! Hoje é {data_hoje}..."
        
        2. CONTEÚDO (Bate-papo fluído):
           - GOIÁS: Foco em políticas públicas, educação e o que acontece em Goiânia.
           
           - ESPORTES (Obrigatório): 
             Fale sobre o VILA NOVA FUTEBOL CLUBE (Tigrão) E sobre o CRUZEIRO ESPORTE CLUBE (Raposa/Cabuloso). 
             Traga as últimas do Vila e do Cruzeiro com igual importância. 
             (Ignore outros times como Flamengo ou Corinthians, a menos que joguem contra Vila ou Cruzeiro).
           
           - BRASIL: Política e economia (foco em justiça, social e mercado).
           
           - MUNDO: Panorama internacional de todos os continentes (África, Ásia, Europa, Américas). Busque diversidade.
           
           - CIÊNCIA/TEC: Uma curiosidade rápida se houver.
        
        3. ENCERRAMENTO: Termine EXATAMENTE com: "Espero que tenha gostado, Yuri. Um ótimo dia para você e até amanhã!"
        
        ESTILO:
        - Conversado, como se fosse um amigo contando as novidades.
        - Use conectivos ("E no mundo da bola, Yuri...", "Agora olhando para fora do país...").
        - NÃO descreva sons.
        
        MATÉRIA PRIMA:
        {news_text}
        """
        
        response = model.generate_content(prompt)
        if response.text:
            return response.text
        return "Tivemos um problema técnico na geração do roteiro."
            
    except Exception as e:
        return f"Erro técnico: {str(e)[:100]}"

async def gen_audio(text, filename):
    clean_text = clean_text_for_speech(text)
    communicate = edge_tts.Communicate(clean_text, "pt-BR-AntonioNeural") 
    await communicate.save(filename)

def update_rss(audio_filename, title):
    rss_file = "feed.xml"
    audio_url = f"{BASE_URL}/{audio_filename}"
    now = datetime.now(pytz.timezone('America/Sao_Paulo'))
    
    safe_title = escape(title).replace("&", "e") 
    
    rss_item = f"""
    <item>
      <title>{safe_title}</title>
      <description>Notícias para Yuri: Vila, Cruzeiro, Goiás e Mundo.</description>
      <enclosure url="{audio_url}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
    </item>
    """
    
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Resumo Diario do Yuri</title>
    <description>Notícias personalizadas.</description>
    <link>{BASE_URL}</link>
    <language>pt-br</language>
    <itunes:image href="https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/640px-Flag_of_Brazil.svg.png"/>
"""
    with open(rss_file, 'w', encoding='utf-8') as f:
        f.write(header + rss_item + "\n  </channel>\n</rss>")

if __name__ == "__main__":
    news = get_news_summary()
    if len(news) > 50:
        script = make_script(news)
        hoje = datetime.now(pytz.timezone('America/Sao_Paulo'))
        filename = f"podcast_{hoje.strftime('%Y%m%d')}.mp3"
        asyncio.run(gen_audio(script, filename))
        update_rss(filename, f"Resumo {hoje.strftime('%d/%m')}")
