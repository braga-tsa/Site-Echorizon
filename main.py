import asyncio
from js import window, document, SpeechSynthesisUtterance, setTimeout, clearTimeout
from pyodide.ffi import create_proxy

leitura = window.speechSynthesis
leituraAtual = None
lendo = False
MDNarracao = False
fontNV = 0

fontTAM = [1, 1.25, 1.55]
fontTT = ['Normal', 'Grande', 'Muito Grande']

indic = document.getElementById('reading-indicator')
lendoLABEL = document.getElementById('reading-label')
toast = document.getElementById('a11y-toast')
btn_leitura = document.getElementById('btn-leitura')
btn_fonte = document.getElementById('btn-fonte')
btn_fundo = document.getElementById('btn-fundo')
btn_narracao = document.getElementById('btn-narracao')

narracao_timeout = None

# Função para remover classes css de destaque
def clear_highlights():
    elements = document.querySelectorAll('.reading-highlight')
    for el in elements:
        el.classList.remove('reading-highlight')

def remove_toast_show():
    toast.classList.remove('show')

# Proxy para o setTimeout do toast
remove_toast_proxy = create_proxy(remove_toast_show)

def show_toast(msg):
    toast.textContent = msg
    toast.classList.add('show')
    setTimeout(remove_toast_proxy, 2200)

def voz_ptbr():
    voices = leitura.getVoices()
    # Converte a coleção JS para uma lista Python iterável
    voices_list = [v for v in voices]
    
    pt_br = next((v for v in voices_list if v.lang == 'pt-BR'), None)
    if pt_br: return pt_br
    
    pt = next((v for v in voices_list if v.lang.startswith('pt')), None)
    if pt: return pt
    
    return voices_list[0] if voices_list else None

def stop_leitura():
    global lendo, MDNarracao
    leitura.cancel()
    lendo = False
    MDNarracao = None
    
    clear_highlights()
    indic.classList.remove('visible')
    btn_leitura.setAttribute('aria-pressed', 'false')
    btn_leitura.classList.remove('active')

def speak_text(text, on_end=None, target_el=None):
    global MDNarracao
    if not leitura:
        show_toast('Seu navegador não suporta síntese de voz.')
        return
    
    leitura.cancel()

    if not text.strip():
        return
    
    narrar = SpeechSynthesisUtterance.new(text) # Instanciação correta no Pyodide
    narrar.lang = 'pt-BR'
    narrar.rate = 0.92
    narrar.pitch = 1
    
    voz = voz_ptbr()
    if voz:
        narrar.voz = voz

    if target_el:
        target_el.classList.add('reading-highlight')
        target_el.scrollIntoView(behavior='smooth', block='nearest')

    # Callbacks de fim e erro de leitura
    def handle_end(event):
        if target_el:
            target_el.classList.remove('reading-highlight')
        if on_end:
            on_end()

    proxy_end = create_proxy(handle_end)
    narrar.onend = proxy_end
    narrar.onerror = proxy_end

    current_utterance = narrar
    leitura.speak(narrar)

def get_readable_blocks():
    elements = document.querySelectorAll('h1, h2, h3, p')
    blocks = []
    for el in elements:
        t = el.innerText.strip()
        if len(t) > 3 and el.closest('header') is None:
            blocks.append(el)
    return blocks

def read_page_sequentially():
    blocks = get_readable_blocks()
    index = 0

    def read_next():
        nonlocal index
        if not lendo or index >= len(blocks):
            stop_leitura()
            show_toast('Leitura concluída ✓')
            return
        
        el = blocks[index]
        index += 1
        reading_label.textContent = f'Lendo parágrafo {index}/{len(blocks)}'
        speak_text(el.innerText.strip(), read_next, el)

    read_next()

# ── LISTENERS DE EVENTOS ──

def handle_btn_leitura(event):
    global lendo
    if not leitura:
        show_toast('Seu navegador não suporta síntese de voz.')
        return

    if lendo:
        stop_leitura()
        show_toast('Leitura pausada')
    else:
        leitura.speak(SpeechSynthesisUtterance.new(''))
        
        def try_start(*args):
            global lendo
            lendo = True
            indic.classList.add('visible')
            btn_leitura.setAttribute('aria-pressed', 'true')
            btn_leitura.classList.add('active')
            show_toast('Iniciando leitura da página...')
            read_page_sequentially()

        if len(leitura.getVoices()) == 0:
            leitura.addEventListener('voiceschanged', create_proxy(try_start), once=True)
        else:
            try_start()

def handle_btn_fonte(event):
    global fontNV
    fontNV = (fontNV + 1) % len(fontTAM)
    scale = fontTAM[fontNV]
    document.documentElement.style.setProperty('--font-scale', str(scale))
    show_toast(f'Fonte: {fontTAM[fontNV]}')

    if MDNarracao:
        speak_text(f'Tamanho da fonte: {fontTAM[fontNV]}')

def handle_btn_fundo(event):
    is_light = document.body.classList.toggle('light-mode')
    btn_fundo.textContent = 'Alterar Fundo 🌙' if is_light else 'Alterar Fundo ☀️'
    show_toast('Modo claro ativado' if is_light else 'Modo escuro ativado')

    if MDNarracao:
        speak_text('Modo claro ativado' if is_light else 'Modo escuro ativado')

def handle_btn_narracao(event):
    global MDNarracao
    MDNarracao = not MDNarracao
    btn_narracao.setAttribute('aria-pressed', 'true' if MDNarracao else 'false')
    btn_narracao.classList.toggle('active', MDNarracao)

    if MDNarracao:
        leitura.speak(SpeechSynthesisUtterance.new(''))
        show_toast('Narração ativada — passe o mouse sobre o texto')
        setTimeout(create_proxy(lambda: speak_text('Modo narração ativado. Passe o mouse sobre o texto.')), 100)
    else:
        stop_leitura()
        show_toast('Narração desativada')

def handle_mouseover(e):
    global narracao_timeout
    if not MDNarracao:
        return

    target = e.target.closest('h1, h2, h3, p, li')
    if not target:
        return

    text = target.innerText.strip()
    if not text or len(text) < 4:
        return

    if narracao_timeout:
        clearTimeout(narracao_timeout)

    def trigger_hover_speech():
        if MDNarracao:
            speak_text(text, None, target)

    narracao_timeout = setTimeout(create_proxy(trigger_hover_speech), 400)

def handle_mouseout(e):
    global narracao_timeout
    if narracao_timeout:
        clearTimeout(narracao_timeout)

def handle_keydown(e):
    if e.key == 'Escape' and lendo:
        stop_leitura()
        show_toast('Leitura interrompida (Esc)')

def handle_focusin(e):
    if not MDNarracao:
        return
    target = e.target.closest('h1, h2, h3, p')
    if not target:
        return
    speak_text(target.innerText.strip(), None, target)

# Registrando os Eventos no DOM usando create_proxy
btn_leitura.addEventListener('click', create_proxy(handle_btn_leitura))
btn_fonte.addEventListener('click', create_proxy(handle_btn_fonte))
btn_fundo.addEventListener('click', create_proxy(handle_btn_fundo))
btn_narracao.addEventListener('click', create_proxy(handle_btn_narracao))

document.addEventListener('mouseover', create_proxy(handle_mouseover))
document.addEventListener('mouseout', create_proxy(handle_mouseout))
document.addEventListener('keydown', create_proxy(handle_keydown))
document.addEventListener('focusin', create_proxy(handle_focusin))
