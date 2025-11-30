import os
import subprocess
import threading
import webbrowser 
from tkinter import Tk, Button, Label, Text, END, Entry, Toplevel, messagebox
from functools import partial 
from urllib.parse import quote 
import time
import datetime 

# --- Importações de Configuração ---
try:
    from dotenv import load_dotenv 
    load_dotenv() 
except ImportError:
    print("Atenção: A biblioteca python-dotenv não está instalada. Execute: pip install python-dotenv")


# --- Importações de Áudio ---
import pyttsx3
import speech_recognition as sr

# --- Importações para Controle Web (Selenium) ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager 
except ImportError:
    print("Atenção: Bibliotecas Selenium ou webdriver-manager não estão instaladas. Execute: pip install selenium webdriver-manager")
    ChromeDriverManager = None

# Importações de IA
try:
    from google import genai
    SYSTEM_PROMPT = """Você é um assistente inteligente. Sua função principal é responder a perguntas gerais. 
    Se o usuário pedir para 'abrir um site' ou 'pesquisar algo', **retorne a URL COMPLETA (incluindo https://)** ou o termo de busca sem qualquer texto adicional.""" 
    
except ImportError:
    print("A biblioteca google-genai não está instalada. Execute: pip install google-genai")
    exit()

# --- VARIÁVEIS DE ESTADO DA GUI E DE CONFIGURAÇÃO ---
assistente_ativo = False
voz_ativa = False
status_label = None
log_text = None
comando_entry = None
root = None
btn_voz = None
client = None 
chat = None 
URL_PREFIXES = ("http://", "https://") 

# --- VARIÁVEIS GLOBAIS DO SELENIUM ---
driver = None 

# --- 1. FUNÇÕES DE ALERTA E CONFIGURAÇÃO DA API ---

def abrir_link_google_ai():
    """Abre a página para o usuário gerar a chave de API."""
    import webbrowser
    webbrowser.open("https://ai.google.dev/gemini-api/docs/api-key") 

def mostrar_alerta_api_ausente(master):
    """Cria e exibe uma janela de alerta se a chave de API não for encontrada."""
    global client
    client = None 

    top = Toplevel(master)
    top.title("⚠️ Chave de API Ausente")
    top.geometry("400x180")
    top.resizable(False, False)
    top.grab_set() 

    Label(top, text="A API do Gemini está desativada.", font=("Helvetica", 12, "bold"), fg="red").pack(pady=10)
    Label(top, text="Variável de ambiente 'GEMINI_API_KEY' não encontrada.", font=("Helvetica", 10)).pack()
    
    Label(top, text="OU Cole sua chave aqui e Salvar:", font=("Helvetica", 9)).pack(pady=(10, 0))
    key_entry = Entry(top, width=40, show="*")
    key_entry.pack()

    btn_frame = Label(top)
    btn_frame.pack(pady=10)
    
    btn_salvar = Button(btn_frame, text="Salvar (Temporário)", command=partial(tentar_salvar_chave, key_entry, top), bg="#4CAF50", fg="white")
    btn_salvar.pack(side='left', padx=5)

    btn_link = Button(btn_frame, text="Gerar Chave Agora", command=abrir_link_google_ai, bg="#FFA500", fg="white")
    btn_link.pack(side='left', padx=5)
    
    master.update_idletasks()
    w = master.winfo_screenwidth()
    h = master.winfo_screenheight()
    x = (w // 2) - (400 // 2)
    y = (h // 2) - (180 // 2)
    top.geometry(f'+{x}+{y}')

    top.wait_window() 

def tentar_salvar_chave(entry_widget, top_level):
    """Tenta configurar a chave colada temporariamente e fechar a janela."""
    chave = entry_widget.get().strip()
    if chave:
        os.environ["GEMINI_API_KEY"] = chave
        exibir_log("Sistema", "Chave de API salva temporariamente. Tentando conectar a IA...", falar_se_ativo=False)
        top_level.destroy() 
    else:
        messagebox.showerror("Erro", "A chave não pode estar vazia.")


def inicializar_gemini(master):
    """Inicializa o cliente Gemini, verificando a chave de API."""
    global client, chat 
    
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Atenção: Variável GEMINI_API_KEY não encontrada. Funcionalidade de IA desativada.")
        if master: 
            mostrar_alerta_api_ausente(master)
        return

    try:
        client = genai.Client(api_key=api_key) 
        # Inicializa o chat e passa o system prompt para a IA
        config = {"system_instruction": SYSTEM_PROMPT} 
        chat = client.chats.create(model="gemini-2.5-flash", config=config) 
        exibir_log("Sistema", "Gemini conectado com sucesso.", falar_se_ativo=False)
    except Exception as e:
        exibir_log("Sistema", f"Erro ao inicializar o Gemini: {e}. A funcionalidade de IA estará desativada.", falar_se_ativo=True)
        client = None

# --- 2. CONFIGURAÇÕES TTS ---
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# --- FUNÇÃO DE SAUDAÇÃO PERSONALIZADA ---
def obter_saudacao():
    """Retorna 'BOM DIA', 'BOA TARDE' ou 'BOA NOITE' com base na hora atual."""
    hora_atual = datetime.datetime.now().hour
    if 5 <= hora_atual < 12:
        return "BOM DIA"
    elif 12 <= hora_atual < 18:
        return "BOA TARDE"
    else:
        return "BOA NOITE"

# --- 3. FUNÇÕES DE VOZ/LOGS ---
def falar(texto):
    """Lê em voz alta."""
    engine.say(texto)
    engine.runAndWait()

def exibir_log(fonte, texto, falar_se_ativo=False):
    """Atualiza a GUI com logs e, opcionalmente, usa TTS."""
    global log_text, voz_ativa
    
    print(f"{fonte}: {texto}")

    if log_text:
        log_text.insert(END, f"\n{fonte}: {texto}")
        log_text.see(END)

    if falar_se_ativo and voz_ativa:
        threading.Thread(target=falar, args=(texto,)).start()

def escutar_comando():
    """Capta o áudio do microfone e o converte em texto em Português."""
    r = sr.Recognizer()
    r.energy_threshold = 500 # Sensibilidade do microfone
    
    try:
        # ✅ CORREÇÃO: O bloco with garante que 'source' seja definido.
        with sr.Microphone() as source:
            # 🔊 Mensagem de escuta retornada com voz
            exibir_log("Sistema", "Escutando... Fale agora.", falar_se_ativo=True)
            # A chamada r.listen() precisa estar dentro do 'with'
            audio = r.listen(source, timeout=7, phrase_time_limit=15) 
    except sr.WaitTimeoutError:
        # 🔊 Mensagem de timeout retornada com voz
        exibir_log("Sistema", "Tempo de escuta esgotado. Nenhuma frase detectada.", falar_se_ativo=True)
        return None
    except Exception as e:
        # Manter como True, pois é um erro crítico.
        exibir_log("Sistema", f"Erro no Microfone: {e}. Desativando voz.", falar_se_ativo=True)
        desativar_voz() 
        return "VOZ_FALHOU"

    try:
        comando = r.recognize_google(audio, language='pt-BR')
        return comando.lower()
    except sr.UnknownValueError:
        exibir_log("Assistente", "Não foi possível entender o áudio.", falar_se_ativo=True)
        return None
    except sr.RequestError as e:
        exibir_log("Assistente", f"Erro de conexão com o Google Speech: {e}", falar_se_ativo=True)
        return None

# --- 4. FUNÇÃO AUXILIAR PARA ABRIR URLS (USANDO SELENIUM COM FALLBACK) ---
def tentar_abrir_url(url_candidata):
    """
    Tenta iniciar o Selenium WebDriver.
    Se falhar, usa o subprocess para abrir diretamente no Chrome/Edge/padrão.
    """
    global driver
    
    # 1. Limpeza e Padronização da URL
    url_limpa = url_candidata.strip()
    
    if not url_limpa.lower().startswith(URL_PREFIXES):
        if '.' in url_limpa or url_limpa.lower().startswith("www."):
            url_limpa = "https://" + url_limpa
        else:
            termo_pesquisa = url_limpa
            exibir_log("Assistente", f"URL inválida retornada pela IA. Pesquisando '{termo_pesquisa}' no Google...", falar_se_ativo=True)
            url_limpa = "https://www.google.com/search?q=" + quote(termo_pesquisa)
    
    exibir_log("Assistente", f"Tentando abrir: {url_limpa}", falar_se_ativo=True)
    
    def abrir_navegador(url):
        global driver
        
        # 1. Fechar o driver anterior se houver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass 
        
        # Tenta a opção Selenium
        if 'webdriver' in globals() and 'ChromeDriverManager' in globals() and ChromeDriverManager is not None:
            try:
                # 🔊 Logs de navegação retornados com voz
                exibir_log("Sistema", "Tentando iniciar o navegador via Selenium...", falar_se_ativo=True)
                service = ChromeService(ChromeDriverManager().install())
                options = webdriver.ChromeOptions()
                options.add_experimental_option("detach", True) 
                
                driver = webdriver.Chrome(service=service, options=options)
                driver.maximize_window()
                driver.get(url)
                # 🔊 Logs de navegação retornados com voz
                exibir_log("Sistema", "Navegador Selenium iniciado com sucesso.", falar_se_ativo=True)
                return
            except WebDriverException as e:
                exibir_log("Sistema", f"Falha no Selenium ({e}). Ativando modo Fallback...", falar_se_ativo=True)
                driver = None
            except Exception as e:
                exibir_log("Sistema", f"Falha desconhecida no Selenium ({e}). Ativando modo Fallback...", falar_se_ativo=True)
                driver = None

        # 2. FALLBACK
        # 🔊 Logs de navegação retornados com voz
        exibir_log("Sistema", "Usando Fallback (Subprocess/Webbrowser) para abrir o navegador...", falar_se_ativo=True)
        try:
            subprocess.Popen(['start', 'chrome', url], shell=True) 
            return
        except FileNotFoundError:
            try:
                subprocess.Popen(['start', 'msedge', url], shell=True)
                return
            except FileNotFoundError:
                try:
                    import webbrowser
                    webbrowser.open(url, new=2, autoraise=True)
                    return
                except Exception as e:
                    exibir_log("Assistente", "ERRO FATAL: Não foi possível abrir a URL em nenhum navegador.", falar_se_ativo=True)
                    print(f"Erro no Fallback: {e}")

    threading.Thread(target=abrir_navegador, args=(url_limpa,)).start()


# --- 4.1 FUNÇÕES DE INTERAÇÃO COM O SITE ---
def interagir_com_site(comando):
    """Executa ações específicas no navegador controlado pelo Selenium."""
    global driver
    
    if driver is None:
        exibir_log("Assistente", "Nenhum site está aberto ou o navegador não foi inicializado. Use 'abra o site...' primeiro.", falar_se_ativo=True)
        return

    comando = comando.lower()

    try:
        if "rolar para baixo" in comando or "descer" in comando:
            exibir_log("Assistente", "Rolando a página para baixo.", falar_se_ativo=True)
            driver.execute_script("window.scrollBy(0, 800);")
            
        elif "rolar para cima" in comando or "subir" in comando:
            exibir_log("Assistente", "Rolando a página para cima.", falar_se_ativo=True)
            driver.execute_script("window.scrollBy(0, -800);")
            
        elif "fechar navegador" in comando or "feche a página" in comando:
            exibir_log("Assistente", "Fechando o navegador.", falar_se_ativo=True)
            driver.quit()
            driver = None
            
        elif "pesquisar por" in comando:
            termo = comando.replace("pesquisar por", "").strip()
            if not termo:
                 exibir_log("Assistente", "Por qual termo você gostaria de pesquisar?", falar_se_ativo=True)
                 return

            exibir_log("Assistente", f"Tentando pesquisar por '{termo}' no site...", falar_se_ativo=True)
            
            try:
                # Tenta encontrar a barra de pesquisa usando seletores comuns
                search_bar = driver.find_element(By.CSS_SELECTOR, 'input[type="text"][name*="q"], input[type="search"], input[id*="search"], input[class*="search"]')
                
                search_bar.send_keys(termo)
                search_bar.send_keys(Keys.RETURN) 
                
                exibir_log("Assistente", "Pesquisa no site executada.", falar_se_ativo=True)

            except Exception:
                exibir_log("Assistente", "Não consegui encontrar uma barra de pesquisa padrão nesta página.", falar_se_ativo=True)

        else:
            exibir_log("Assistente", "Comando de interação no site não reconhecido. Tente 'rolar para baixo' ou 'pesquisar por [termo]'.", falar_se_ativo=True)

    except Exception as e:
        exibir_log("Assistente", f"Erro durante a interação com o site: {e}", falar_se_ativo=True)


# --- 5. FUNÇÃO DE PROCESSAMENTO DE COMANDOS (CENTRAL) ---

def processar_comando(comando):
    """Executa ações do sistema, interage com o site ou envia para a IA do Gemini."""
    global voz_ativa
    
    if not assistente_ativo:
        # 🔊 Mensagem de sistema retornada com voz
        exibir_log("Sistema", "Assistente está inativo. Ative para processar comandos.", falar_se_ativo=True)
        return
        
    exibir_log("Comando", comando)

    comando = comando.lower()

    # --- 5.0. COMANDO DE INTERAÇÃO COM O SITE (PRIORIDADE MÁXIMA) ---
    if driver is not None and ("rolar" in comando or "fechar navegador" in comando or "pesquisar por" in comando or "subir" in comando or "descer" in comando):
        threading.Thread(target=interagir_com_site, args=(comando,)).start()
        return


    # --- 5.1. COMANDO DE PESQUISA GERAL (Google) ---
    if "pesquise" in comando or "procure" in comando or "busque" in comando:
        
        palavras_chave_remover = ["pesquise", "procure", "busque", "por", "sobre", "e", "o", "a", "no", "na"]
        termo_pesquisa = comando
        
        for p in palavras_chave_remover:
            termo_pesquisa = termo_pesquisa.replace(f" {p} ", " ").strip()
            
        if not termo_pesquisa:
            termo_pesquisa = comando 
            
        exibir_log("Assistente", f"Pesquisando '{termo_pesquisa}' no Google...", falar_se_ativo=True)

        url_pesquisa = "https://www.google.com/search?q=" + quote(termo_pesquisa)
        
        tentar_abrir_url(url_pesquisa) 
        return

    # --- 5.2. COMANDO DE ABRIR SITE DIRETO ---
    if ("abra" in comando or "abrir" in comando) and ("site" in comando or "página" in comando or "url" in comando or len(comando.split()) <= 4):
        if not client:
            exibir_log("Assistente", "A IA não está conectada. Verifique sua chave Gemini.", falar_se_ativo=True)
            return

        exibir_log("Assistente", "Solicitando URL à Inteligência Artificial...", falar_se_ativo=True)
        try:
            # A IA retorna a URL pura devido ao SYSTEM_PROMPT
            resposta_ia = chat.send_message(comando)
            url_candidata = resposta_ia.text.strip()
            
            # Se a resposta da IA for um URL, abra-o imediatamente.
            if url_candidata.lower().startswith(URL_PREFIXES) or '.' in url_candidata:
                tentar_abrir_url(url_candidata) 
            # Se a IA pedir mais informação, exibe a mensagem.
            else:
                 exibir_log("Gemini", url_candidata, falar_se_ativo=True)
            
        except Exception as e:
            exibir_log("Assistente", "Houve um erro de comunicação com a IA ao buscar o site.", falar_se_ativo=True)
            print(f"Erro Gemini ao buscar URL: {e}")
            
        return 

    # --- 5.3. Comandos de Sistema (Abrir Programas) ---
    if "abra" in comando or "abrir" in comando:
        
        if "bloco de notas" in comando:
            exibir_log("Assistente", "Abrindo o Bloco de Notas.", falar_se_ativo=True)
            subprocess.Popen("notepad.exe")
        
        elif "explorador de arquivos" in comando or "gerenciador de arquivos" in comando:
            exibir_log("Assistente", "Abrindo o Explorador de Arquivos.", falar_se_ativo=True)
            subprocess.Popen("explorer")
        elif "calculadora" in comando:
            exibir_log("Assistente", "Abrindo a Calculadora.", falar_se_ativo=True)
            subprocess.Popen("calc.exe")
        elif "paint" in comando:
            exibir_log("Assistente", "Abrindo o Paint.", falar_se_ativo=True)
            subprocess.Popen("mspaint.exe")
        elif "meu programa isa" in comando:
            caminho_programa_isa = r"C:\Caminho\Exato\Para\Seu\ProgramaISA.exe" 
            try:
                exibir_log("Assistente", "Iniciando o seu programa personalizado, ISA.", falar_se_ativo=True)
                subprocess.Popen(caminho_programa_isa)
            except FileNotFoundError:
                exibir_log("Assistente", "Erro: Não encontrei o arquivo do programa ISA no caminho especificado. Verifique o caminho no código.", falar_se_ativo=True)
        else:
            exibir_log("Assistente", "Desculpe, não sei como abrir isso.", falar_se_ativo=True)
        return

    # --- 5.4. Comandos de Encerrar ---
    elif "sair" in comando or "encerrar" in comando or "desligar aplicação" in comando:
        exibir_log("Assistente", "Encerrando a aplicação e fechando o navegador, se estiver aberto. Até logo!", falar_se_ativo=True)
        if driver:
              try:
                driver.quit()
              except Exception:
                pass
        if root:
            root.quit()
        return
        
    # --- 5.5. Comandos de Conversa Geral (Fallback para Gemini) ---
    elif client: 
        try:
            exibir_log("Assistente", "Consultando a inteligência artificial...", falar_se_ativo=True) 
            response = chat.send_message(comando)
            exibir_log("Gemini", response.text, falar_se_ativo=True)
        except Exception as e:
            exibir_log("Assistente", "Desculpe, houve um erro ao processar sua pergunta com a IA.", falar_se_ativo=True)
            print(f"Erro Gemini: {e}")
            
    else:
        exibir_log("Assistente", "Comando não mapeado. A IA (Gemini) não está disponível.", falar_se_ativo=True)

# --- 6. FUNÇÃO PRINCIPAL DO MODO VOZ (LOOP) ---

def laço_principal_voz():
    """Roda o loop de escuta de voz em uma thread separada."""
    global voz_ativa, assistente_ativo
    
    if not assistente_ativo:
        # 🔊 Mensagem de sistema retornada com voz
        exibir_log("Sistema", "Assistente principal não está ativo. Ative o software primeiro.", falar_se_ativo=True)
        desativar_voz()
        return

    # 🔊 Mensagem de sistema retornada com voz
    exibir_log("Sistema", "Modo VOZ ativado. Iniciando escuta...", falar_se_ativo=True)
    
    while voz_ativa:
        comando_usuario = escutar_comando()
        
        if comando_usuario and comando_usuario != "VOZ_FALHOU":
            exibir_log("Você disse", comando_usuario)
            processar_comando(comando_usuario)
        
        if comando_usuario == "VOZ_FALHOU":
            break
        
        time.sleep(0.5)
        
    # 🔊 Mensagem de sistema retornada com voz
    exibir_log("Sistema", "Modo VOZ desativado.", falar_se_ativo=True)
    root.after(100, atualizar_status_voz)


# --- 7. FUNÇÕES DE CONTROLE DA GUI ---

def enviar_comando_gui(event=None):
    """Lê o texto da caixa de entrada e chama o processador."""
    global comando_entry
    comando = comando_entry.get().strip()
    
    if comando:
        processar_comando(comando)
        comando_entry.delete(0, END)

def atualizar_status_principal():
    """Atualiza o status visual do software principal."""
    global status_label, botao_toggle, comando_entry
    if assistente_ativo:
        status_label.config(text="ATIVO: Pronto para Comandos", bg="#008000", fg="white")
        botao_toggle.config(text="Desativar Software", command=desativar_assistente, bg="#FF6347")
        comando_entry.config(state='normal')
    else:
        status_label.config(text="INATIVO: Clique para Ativar", bg="#8B0000", fg="white")
        botao_toggle.config(text="Ativar Software", command=ativar_assistente, bg="#4CAF50")
        comando_entry.config(state='disabled')
        desativar_voz() 

def ativar_assistente():
    """Ativa o modo de gerenciamento/uso (software principal)."""
    global assistente_ativo
    if not assistente_ativo:
        assistente_ativo = True
        # 🔊 Mensagem de sistema retornada com voz
        exibir_log("Sistema", "Software principal ativado.", falar_se_ativo=True)
        atualizar_status_principal()

def desativar_assistente():
    """Desativa o modo de gerenciamento/uso (software principal)."""
    global assistente_ativo
    if driver:
          try:
            driver.quit()
          except Exception:
            pass
    assistente_ativo = False
    # 🔊 Mensagem de sistema retornada com voz
    exibir_log("Sistema", "Software principal desativado.", falar_se_ativo=True)
    atualizar_status_principal()

def atualizar_status_voz():
    """Atualiza o status visual do botão de voz."""
    global btn_voz
    if voz_ativa:
        btn_voz.config(text="Voz: ATIVA (Ouvindo)", bg="#00BFFF", state='normal') 
    else:
        btn_voz.config(text="Voz: INATIVA (Microfone Off)", bg="#696969", state='normal') 

def ativar_voz():
    """Liga o modo voz e inicia o loop de escuta em uma thread."""
    global voz_ativa, assistente_ativo
    if not assistente_ativo:
        # 🔊 Mensagem de sistema retornada com voz
        exibir_log("Sistema", "Ative o software principal primeiro.", falar_se_ativo=True)
        return
        
    if not voz_ativa:
        # Tenta inicializar o microfone para checar a disponibilidade
        try:
            temp_r = sr.Recognizer()
            temp_mic = sr.Microphone()
            with temp_mic as source:
                pass 
        except Exception:
            messagebox.showwarning("Atenção", "Microfone não encontrado. Verifique se o dispositivo está conectado e configurado como padrão no Windows.")
            return 

        voz_ativa = True
        t = threading.Thread(target=laço_principal_voz)
        t.daemon = True 
        t.start()
        atualizar_status_voz()
        
def desativar_voz():
    """Desliga o modo voz."""
    global voz_ativa
    if voz_ativa:
        voz_ativa = False
    atualizar_status_voz()

# --- 8. CRIAÇÃO DA INTERFACE GRÁFICA (Tkinter) ---
if __name__ == "__main__":
    root = Tk()
    root.title("🤖 Gerenciador de Software ISA (Modo Híbrido)")
    root.geometry("450x600")
    root.resizable(False, False)

    # 8.1. Rótulo de Status (Software Principal)
    status_label = Label(root, text="", font=("Helvetica", 14, "bold"), pady=10)
    status_label.pack(fill='x', padx=10, pady=(10, 5))

    # 8.2. Botão de Ativação/Desativação do SOFTWARE
    botao_toggle = Button(root, text="", font=("Helvetica", 10), fg="white")
    botao_toggle.pack(fill='x', padx=10, pady=5)
    
    # 8.3. Botão de Ativação/Desativação do MODO VOZ 
    btn_voz = Button(root, text="Voz: INATIVA (Microfone Off)", command=ativar_voz, font=("Helvetica", 10, "bold"), bg="#696969", fg="white")
    btn_voz.pack(fill='x', padx=10, pady=5)

    # 8.4. Área de Entrada de Comandos de Texto
    entrada_frame = Label(root)
    entrada_frame.pack(fill='x', padx=10, pady=(15, 5))

    Label(entrada_frame, text="Comando de Texto:", font=("Helvetica", 10)).pack(side='left', padx=(0, 5))

    comando_entry = Entry(entrada_frame, width=30, font=("Helvetica", 10), state='disabled')
    comando_entry.pack(side='left', fill='x', expand=True)
    comando_entry.bind('<Return>', enviar_comando_gui)

    botao_enviar = Button(entrada_frame, text="Enviar", command=enviar_comando_gui, font=("Helvetica", 10), bg="#006400", fg="white")
    botao_enviar.pack(side='right', padx=(5, 0))

    # 8.5. Área de Log
    log_title = Label(root, text="Histórico de Comandos e Respostas:", font=("Helvetica", 10, "underline"))
    log_title.pack(pady=(10, 0))

    log_text = Text(root, height=18, width=50, state='normal', bg="#f0f0f0", wrap='word', font=("Helvetica", 9))
    log_text.insert(END, "Bem-vindo ao Gerenciador de Software ISA.\n")
    
    # 🎤 Saída inicial de voz da ISA
    saudacao_do_dia = obter_saudacao()
    mensagem_inicial = f"{saudacao_do_dia}! SOU A ASSISTENTE VIRTUAL ISA, COMO POSSO LHE AJUDAR?"
    
    # 1. Insere no log de texto
    log_text.insert(END, f"\nAssistente: {mensagem_inicial}")
    
    # 2. Força a resposta por voz na inicialização
    threading.Thread(target=falar, args=(mensagem_inicial,)).start()
    
    log_text.pack(padx=10, pady=10)

    # Inicializa o status e a API
    inicializar_gemini(root) 
    atualizar_status_principal()
    atualizar_status_voz()

    # Inicia o loop da interface gráfica
    root.mainloop()

    # --- FINALIZAÇÃO ---
    engine.stop()
    # Garante que o driver seja fechado ao sair
    if driver:
          try:
            driver.quit()
          except Exception:
            pass