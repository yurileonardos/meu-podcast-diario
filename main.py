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
GITHUB_USER = "yurileonardos"  # <--- COLOQUE SEU USUÁRIO AQUI
REPO_NAME = "meu-podcast-diario"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# --- MEGABANCO DE FONTES (Curadoria Yuri Completa) ---
FEEDS = {
    "GOIÁS (Cotidiano, Clima, Política)": [
        "https://g1.globo.com/rss/g1/goias/",
        "https://www.jornalopcao.com.br/feed/",
        "https://www.maisgoias.com.br/feed/",
        "https://opopular.com.br/rss",
        "https://www.dm.com.br/feed"
    ],
    "ESPORTES (Vila Nova & Cruzeiro)": [
        "https://ge.globo.com/rss/ge/futebol/times/vila-nova/",   
        "https://ge.globo.com/rss/ge/futebol/times/cruzeiro/",
        "https://www.maisgoias.com.br/category/esportes/vila-nova/feed/"
    ],
    "CONCURSOS E OPORTUNIDADES": [
        "https://g1.globo.com/rss/g1/concursos-e-emprego/",
        "https://jcconcursos.com.br/rss/noticias"
    ],
    "BRASIL (Política, Justiça, Social)": [
        "https://rss.uol.com.br/feed/noticias.xml",
        "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "https://www.estadao.com.br/rss/politica",
        "https://www.cnnbrasil.com.br/feed/",
        "https://www.brasil247.com/feed",
        "https://cartacapital.com.br/feed/",
        "https://agenciabrasil.ebc.com.br/rss/ultimas-noticias/feed.xml",
        "https://www.camara.leg.br/noticias/rss/ultimas-noticias",
        "https://www12.senado.leg.br/noticias/feed/todas/rss"
    ],
    "MUNDO (Geopolítica Global)": [
        "https://brasil.elpais.com/rss/elpais/america.xml",      
        "https://www.bbc.com/portuguese/index.xml",              
        "https://rss.dw.com/xml/rss-br-all",                     
        "https://news.un.org/feed/subscribe/pt/news/all/rss.xml", 
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", 
        "https://www.theguardian.com/world/rss"                  
    ],
    "CIÊNCIA, TECNOLOGIA E IA": [
        "https://super.abril.com.br/feed/",
        "https://exame.com/feed/",
        "https://gizmodo.uol.com.br/feed/",
        "https://www.nature.com/nature.rss"
    ]
}

def get_news_summary():
    texto_final = ""
    print("Coletando notícias de todas as áreas...")
    for categoria, urls in FEEDS.items():
        texto_final += f"\n--- {categoria} ---\n"
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # Pega 3 notícias de cada para garantir variedade sem estourar limite
                for entry in feed.entries[:3]:
                    title = entry.title
                    summary = entry.summary if 'summary' in entry else ""
                    summary = re.sub(r'<[^>]+>', '', summary)[:250]
                    
                    source_name = "Fonte Desconhecida"
                    if 'source' in entry: source_name = entry.source.title
                    elif 'feed' in feed and 'title' in feed.feed: source_name = feed.feed.title
                    
                    texto_final += f"[{source_name}] {title}: {summary}\n"
            except: continue
    return texto_final

def clean_text_for_speech(text):
    text = text.replace("*", "")
    text = text.replace("#", "")
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'http\S+', '', text)
    text = text.replace("BRL", "reais")
    text = text.replace("USD", "dólares")
    return text

def make_script(news_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

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
        
        # PROMPT COMPLETO COM TODOS OS REQUISITOS DO YURI
        prompt = f"""
        Você é o âncora pessoal do Yuri. Data: {data_hoje}.
        
        SUA MISSÃO: Cruzar informações de várias fontes e criar um resumo rico e sério.
        
        1. SAUDAÇÃO: "Olá, bom dia Yuri! Aqui é o seu mixer diário de notícias. Hoje é {data_hoje}." (Cite o nome APENAS aqui).
        
        2. BLOCOS OBRIGATÓRIOS (Aborde todos se houver notícias):
           
           - GOIÁS & GOIÂNIA:
             * Foco total em: Políticas públicas estaduais/municipais, ações do Governo/Prefeitura.
             * Questões sociais, educação e saúde em Goiás.
             * CLIMA: Se houver informação nas fontes locais, informe a previsão do tempo para Goiânia.
           
           - ESPORTE (VILA NOVA & CRUZEIRO):
             * Prioridade absoluta para o Tigrão (Vila) e a Raposa (Cruzeiro).
             * Ignore outros times.
           
           - BRASIL (POLÍTICA & SOCIEDADE):
             * Ações de Estado, Justiça, Segurança Pública e Economia.
             * Mercado de trabalho e Questões Sociais.
           
           - OPORTUNIDADES:
             * CONCURSOS PÚBLICOS: Destaque editais abertos ou notícias relevantes de carreira.
           
           - INOVAÇÃO & FUTURO:
             * Inteligência Artificial, Tecnologia, Ciência e Inovação.
           
           - MUNDO (GEOPOLÍTICA):
             * Panorama global (Américas, Europa, África, Ásia). Traduza e resuma as fontes internacionais.
        
        3. DESPEDIDA: "Espero que tenha gostado. Um ótimo dia e até amanhã!"
        
        ESTILO:
        - Tom de conversa inteligente.
        - Cruze as fontes (ex: "Enquanto a Folha diz X, a Gazeta aponta Y").
        - Seja direto e informativo.
        
        DADOS BRUTOS:
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
      <description>Resumo diário completo: Goiás, Vila, Cruzeiro, Política, Concursos e Mundo.</description>
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
