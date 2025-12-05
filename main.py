import os
import feedparser
import google.generativeai as genai
import asyncio
import edge_tts
from datetime import datetime
import pytz
from xml.sax.saxutils import escape
import re
import urllib.request

# --- CONFIGURAÇÕES DO USUÁRIO ---
GITHUB_USER = "yurileonardos"  # <--- SEU USUÁRIO AQUI
REPO_NAME = "meu-podcast-diario"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# --- FONTES (Mantivemos sua lista completa) ---
FEEDS = {
    "GOIÁS (Política, Cotidiano)": [
        "https://g1.globo.com/rss/g1/goias/",
        "https://www.jornalopcao.com.br/feed/",
        "https://www.maisgoias.com.br/feed/",
        "https://opopular.com.br/rss",
        "https://diariodegoias.com.br/feed/",
        "https://ohoje.com/feed/"
    ],
    "ESPORTES (Vila Nova & Cruzeiro)": [
        "https://ge.globo.com/rss/ge/futebol/times/vila-nova/",   
        "https://ge.globo.com/rss/ge/futebol/times/cruzeiro/",
        "https://www.maisgoias.com.br/category/esportes/vila-nova/feed/"
    ],
    "CONCURSOS": [
        "https://g1.globo.com/rss/g1/concursos-e-emprego/",
        "https://jcconcursos.com.br/rss/noticias",
        "https://www.pciconcursos.com.br/feed"
    ],
    "BRASIL (Política, Economia, Social)": [
        "https://rss.uol.com.br/feed/noticias.xml",
        "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "https://www.estadao.com.br/rss/politica",
        "https://www.cnnbrasil.com.br/feed/",
        "https://www.brasil247.com/feed",
        "https://cartacapital.com.br/feed/",
        "https://agenciabrasil.ebc.com.br/rss/ultimas-noticias/feed.xml",
        "https://www.camara.leg.br/noticias/rss/ultimas-noticias",
        "https://www12.senado.leg.br/noticias/feed/todas/rss",
        "https://iclnoticias.com.br/feed/",
        "https://veja.abril.com.br/feed/",
        "https://exame.com/feed/",
        "https://piaui.folha.uol.com.br/feed/",
        "https://www.metropoles.com/feed"
    ],
    "MUNDO (Geopolítica Profunda)": [
        "https://brasil.elpais.com/rss/elpais/america.xml",      
        "https://www.bbc.com/portuguese/index.xml",              
        "https://rss.dw.com/xml/rss-br-all",                     
        "https://news.un.org/feed/subscribe/pt/news/all/rss.xml", 
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", 
        "https://www.theguardian.com/world/rss",
        "https://www.clarin.com/rss/lo-ultimo/",
        "https://pt.euronews.com/rss?format=xml"
    ],
    "CIÊNCIA, TECNOLOGIA E SAÚDE": [
        "https://super.abril.com.br/feed/",
        "https://gizmodo.uol.com.br/feed/",
        "https://www.nature.com/nature.rss",
        "https://saude.abril.com.br/feed/"
    ],
    "YOUTUBE (Canais)": [
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCO6j6cqBhi2TWVxfcn6t23w", 
        "https://www.youtube.com/feeds/videos.xml?channel_id=UC6w8cK5C5QZJ9J9J9J9J9J9" 
    ]
}

# --- LINKS DO INMET/CLIMATEMPO (HTML) ---
WEATHER_URLS = [
    "https://portal.inmet.gov.br/", 
    "https://www.climatempo.com.br/previsao-do-tempo/15-dias/cidade/88/goiania-go"
]

def get_data_ptbr():
    now = datetime.now(pytz.timezone('America/Sao_Paulo'))
    dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    meses = ['', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    return f"{now.day} de {meses[now.month]}, uma {dias[now.weekday()]}"

def get_weather_data():
    text_data = "\n--- DADOS DE CLIMA (INMET/CLIMATEMPO) ---\n"
    print("Consultando INMET...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in WEATHER_URLS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                # Pega mais conteúdo do HTML para garantir que pegamos a previsão
                clean = re.sub(r'<[^>]+>', ' ', html)
                clean = re.sub(r'\s+', ' ', clean)
                text_data += f"Fonte ({url}): {clean[:4000]}...\n"
        except: continue
    return text_data

def get_news_summary():
    texto_final = ""
    print("Coletando notícias (Modo Aprofundado)...")
    for categoria, urls in FEEDS.items():
        texto_final += f"\n--- {categoria} ---\n"
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # AUMENTO DE VOLUME: Pega 4 notícias e MUITO mais texto de cada uma
                for entry in feed.entries[:4]:
                    title = entry.title
                    # Tenta pegar o conteúdo completo se disponível, senão o resumo
                    content = entry.summary
                    if 'content' in entry:
                        content = entry.content[0].value
                    
                    # AUMENTO DE LIMITE: 1500 caracteres por notícia (antes era 200)
                    summary = re.sub(r'<[^>]+>', '', content)[:1500]
                    
                    published = entry.published if 'published' in entry else "Data Recente"
                    source_name = "Fonte"
                    if 'source' in entry: source_name = entry.source.title
                    elif 'feed' in feed and 'title' in feed.feed: source_name = feed.feed.title
                    
                    texto_final += f"[{source_name} | {published}] {title}: {summary}\n"
            except: continue
            
    texto_final += get_weather_data()
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
        data_hoje_extenso = get_data_ptbr()
        
        # --- PROMPT "PROGRAMA DE RÁDIO LONGO" ---
        prompt = f"""
        ATUE COMO: Um âncora de rádio inteligente, profundo e detalhista.
        OUVINTE: Yuri.
        DATA: {data_hoje_extenso}.
        OBJETIVO: Criar um podcast LONGO (mais de 10 minutos de leitura).
        
        INSTRUÇÕES DE PERSONALIDADE:
        - NÃO SEJA RESUMIDO. O Yuri quer detalhes. Explique o "porquê" das coisas.
        - Fale devagar, use pausas e conectivos de qualidade ("Analisando profundamente...", "Isso impacta diretamente...").
        - Se a notícia for de dias atrás (especialmente Esporte), traga ela à tona e analise o contexto atual.
        
        ROTEIRO OBRIGATÓRIO (Cubra TODOS os pontos com calma):
        
        1. ABERTURA:
           - "Olá, bom dia Yuri! Hoje é {data_hoje_extenso}. Prepare-se para um mergulho profundo nas notícias."
        
        2. CLIMA EM GOIÂNIA (Análise Completa):
           - Leia os dados brutos do INMET/Climatempo abaixo.
           - Informe temperatura máxima/mínima, umidade, ventos e probabilidade de chuva.
           - Dê dicas (ex: "Leve guarda-chuva", "Hidrate-se").
        
        3. ESPORTE - VILA NOVA & CRUZEIRO (Bloco Especial):
           - Destaque TOTAL para o Tigrão e a Raposa.
           - Se não houver jogo hoje, fale das contratações, do treino da semana, da situação na tabela.
           - Invente análises baseadas nos fatos: "O técnico precisa ajustar a defesa...", etc.
        
        4. GOIÁS & CIDADES (Política e Social):
           - Aprofunde nas decisões do Governo Estadual e Prefeitura.
           - Comente obras, trânsito e questões sociais.
        
        5. BRASIL - POLÍTICA & ECONOMIA (Bloco Denso):
           - Não leia manchetes. Explique as intrigas do Congresso, as decisões do STF e o impacto econômico.
           - Cruze fontes: O que a esquerda e a direita estão dizendo?
        
        6. CENÁRIO INTERNACIONAL (Geopolítica):
           - Fale da Guerra na Ucrânia, Oriente Médio ou tensões nos EUA/China.
           - Explique o impacto global desses conflitos.
        
        7. CIÊNCIA, SAÚDE & TECNOLOGIA:
           - Escolha uma notícia de avanço médico ou tecnológico e explique como isso muda o futuro.
        
        8. OPORTUNIDADES:
           - Cite concursos abertos relevantes.
        
        9. DESPEDIDA:
           - "Espero que tenha gostado desta análise completa, Yuri. Um ótimo dia e até amanhã!"
        
        DADOS BRUTOS (Use isso para criar sua análise):
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
      <description>Edição Completa e Aprofundada para Yuri.</description>
      <enclosure url="{audio_url}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
    </item>
    """
    
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Resumo Diario do Yuri</title>
    <description>Notícias aprofundadas.</description>
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
