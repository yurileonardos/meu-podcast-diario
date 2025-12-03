import os
import feedparser
import google.generativeai as genai
import asyncio
import edge_tts
from datetime import datetime
import pytz
from xml.sax.saxutils import escape
import re # Ferramenta de limpeza de texto

# --- CONFIGURAÇÕES DO USUÁRIO ---
GITHUB_USER = "yurileonardos"  # <--- COLOQUE SEU USUÁRIO AQUI
REPO_NAME = "meu-podcast-diario"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# --- FONTES ---
FEEDS = {
    "GOIÁS (Política e Cotidiano)": [
        "https://g1.globo.com/rss/g1/goias/",
        "https://www.jornalopcao.com.br/feed/",
        "https://www.maisgoias.com.br/feed/"
    ],
    "BRASIL (Política, Justiça, Economia)": [
        "https://www.brasil247.com/feed",
        "https://cartacapital.com.br/feed/",
        "https://agenciabrasil.ebc.com.br/rss/ultimas-noticias/feed.xml",
        "https://feeds.folha.uol.com.br/poder/rss091.xml"
    ],
    "CIÊNCIA E TECNOLOGIA": [
        "https://super.abril.com.br/feed/",
        "https://gizmodo.uol.com.br/feed/",
    ],
    "ESPORTES (Filtro Específico)": [
        "https://ge.globo.com/rss/ge/futebol/times/vila-nova/", # Vila Nova
        "https://ge.globo.com/rss/ge/futebol/times/cruzeiro/"   # Cruzeiro
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
                for entry in feed.entries[:4]: # Pega 4 de cada para ter variedade
                    title = entry.title
                    summary = entry.summary if 'summary' in entry else ""
                    # Limpa HTML básico
                    summary = re.sub(r'<[^>]+>', '', summary)[:300]
                    texto_final += f"- {title}: {summary}\n"
            except: continue
    return texto_final

# --- FUNÇÃO DE LIMPEZA DE VOZ (NOVO) ---
def clean_text_for_speech(text):
    # Remove marcações de Markdown que o robô lê errado
    text = text.replace("*", "") # Remove asteriscos
    text = text.replace("#", "") # Remove hashtags
    text = re.sub(r'\[.*?\]', '', text) # Remove coisas entre colchetes ex: [Música]
    text = re.sub(r'http\S+', '', text) # Remove links de internet
    text = text.replace("BRL", "reais") # Melhora leitura de moeda
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
        
        # PROMPT REFINADO (Estilo NotebookLM / Bate-Papo)
        prompt = f"""
        Aja como um podcaster inteligente e carismático. 
        Data de hoje: {data_hoje}.
        
        SEU OBJETIVO:
        Criar um roteiro de áudio fluído, parecendo um bate-papo direto com o ouvinte (estilo "NotebookLM" ou rádio moderna). NÃO PAREÇA UM ROBÔ LENDO LISTA.
        
        REGRAS DE CONTEÚDO (CRUCIAL):
        1. Filtre APENAS estes temas: Políticas públicas, educação, tecnologia, ciência, economia, saúde, segurança, justiça, geopolítica, meio ambiente.
        2. ESPORTES: Fale APENAS sobre VILA NOVA ou CRUZEIRO. Ignore qualquer outro time (Flamengo, Corinthians, etc). Se não tiver notícia do Vila ou Cruzeiro, não fale de esporte.
        3. Ignore fofocas, novelas e celebridades.
        
        ESTILO DE FALA:
        - Não use "Bom dia ouvinte". Comece direto no assunto: "Olá, hoje é {data_hoje} e vamos falar sobre..."
        - Use frases de conexão: "Mudando de assunto...", "Olha que interessante...", "No cenário econômico...".
        - NÃO descreva sons (Ex: não escreva [Música sobe], não escreva *risos*). Escreva APENAS o que deve ser falado.
        - Não leia manchetes. Explique a notícia.
        
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
    # Limpa o texto antes de enviar para a voz
    clean_text = clean_text_for_speech(text)
    # Voz 'Antonio' é mais jornalística/séria. 'Francisca' é mais suave.
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
      <description>Notícias de Goiás, Brasil e Mundo.</description>
      <enclosure url="{audio_url}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
    </item>
    """
    
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Resumo Diario Personalizado</title>
    <description>Goiás, Brasil, Mundo e Esportes Selecionados.</description>
    <link>{BASE_URL}</link>
    <language>pt-br</language>
    <itunes:image href="https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/640px-Flag_of_Brazil.svg.png"/>
"""
    # Força recriação do XML para limpar cache antigo
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
