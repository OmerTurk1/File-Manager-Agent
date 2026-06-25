let eventSource = null;
let currentToolWrapper = null;
const logoTextSize = 15;
const contentTextSize = 14;
const TOOL_FONT_RATIO = 0.85;

// Sayfa yüklendiğinde mevcut ayarları backend'den çekip inputlara doldur
window.addEventListener('DOMContentLoaded', async () => {
    try {
        // İsteğe bağlı: Backend'de mevcut ayarları dönen bir /get_current_preferences rotası yazarsan 
        // buradaki inputları otomatik doldurabilirsin.
    } catch (err) {
        console.error("Ayarlar yüklenirken hata oluştu:", err);
    }
});

// 1. Ayarları Kaydetme (POST request)
async function savePreferences() {
    const data = {
        MAIN_ROOT_FOLDER: document.getElementById('pref-root').value,
        VIEWABLE_FOLDER_ROOT: document.getElementById('pref-viewable').value,
        FRONT_CHARS: parseInt(document.getElementById('pref-front').value) || 12,
        BACK_CHARS: parseInt(document.getElementById('pref-back').value) || 10,
        OPENAI_API_KEY: document.getElementById('pref-key').value || null
    };

    try {
        const response = await fetch('/adjust_preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const resData = await response.json();
        if(resData.status === 'success') {
            appendLog('system', 'Ayarlar başarıyla güncellendi ve kaydedildi.');
        }
    } catch (err) {
        appendLog('error', 'Ayarlar kaydedilirken hata oluştu: ' + err);
    }
}

// 2. SSE Bağlantısını Başlatma ve Canlı Log Akışı
function startAgentTask() {
    const inputField = document.getElementById('user-input');
    const userInput = inputField.value.trim();
    if (!userInput) return;

    if (eventSource) {
        eventSource.close();
    }

    const terminal = document.getElementById('terminal');
    const statusBadge = document.getElementById('status-badge');
    const runBtn = document.getElementById('run-btn');

    appendLog('user', userInput); // Kullanıcı sorusunu mavi balonla başlat

    statusBadge.innerText = "Status: Running...";
    statusBadge.className = "text-xs font-mono text-amber-400 bg-amber-950/30 border border-amber-900/50 px-3 py-1 rounded-full";
    runBtn.disabled = true;
    runBtn.classList.add('opacity-50', 'cursor-not-allowed');
    inputField.value = '';

    // SSE EventSource başlatılıyor
    eventSource = new EventSource(`/chat_stream?user_input=${encodeURIComponent(userInput)}`);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.event === "tool_call") {
            // Yeni bir araç çağrısı başladığında balon oluştur ve referansı sakla
            currentToolWrapper = appendToolCallLog(data.tool_name, data.inputs);
        } 
        else if (data.event === "tool_result") {
            // Çıktı başarılı geldiyse sakladığımız balona ekle ve logoyu yeşil yap
            if (currentToolWrapper) {
                updateToolResultLog(currentToolWrapper, data.output, false);
            } else {
                // Güvenlik önlemi: Eğer call gelmeden direkt result gelirse sıfırdan oluşturur
                currentToolWrapper = appendToolCallLog("Unknown Tool", {});
                updateToolResultLog(currentToolWrapper, data.output, false);
            }
        } 
        else if (data.event === "tool_error") {
            // Hata geldiyse balona ekle ve logoyu kırmızı yap
            if (currentToolWrapper) {
                updateToolResultLog(currentToolWrapper, data.message, true);
            } else {
                currentToolWrapper = appendToolCallLog("Unknown Tool", {});
                updateToolResultLog(currentToolWrapper, data.message, true);
            }
        }
        else if (data.event === "final_answer") {
            appendLog('final_answer', data.message);
            appendLog('usage', `[Token Tüketimi] Prompt: ${data.usage.total_prompt_tokens} | Completion: ${data.usage.total_completion_tokens} | Toplam: ${data.usage.total_token_consumption}`);
            endTask("Success");
        } 
        else if (data.event === "error") {
            appendLog('error', `[HATA] ➔ ${data.message}`);
            endTask("Error");
        }
    };

    eventSource.onerror = function(err) {
        console.error("EventSource hatası meydana geldi:", err);
        appendLog('error', `[Sistem Hatası] Bağlantı koptu veya sunucu hata döndürdü.`);
        endTask("Failed");
    };
}

function appendToolCallLog(toolName, inputs) {
    const terminal = document.getElementById('terminal');
    const wrapper = document.createElement('div');
    wrapper.className = "flex space-x-3 items-start my-3 w-full animate-fade-in";
    
    // Sol taraftaki Dişli logosu (Varsayılan olarak süreç devam ettiği için turuncu border/arka plan)
    const logoHTML = `
        <div class="tool-logo flex-shrink-0 w-7 h-7 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 text-xs transition-colors duration-300">
            ⚙️
        </div>`;
        
    // İçerik alanı (Turuncu temalı araç çağrı kutusu)
    const contentHTML = `
        <div class="flex-1 bg-amber-950/10 border border-amber-900/30 p-3 rounded-xl max-w-3xl space-y-2">
            <div class="text-amber-400 font-mono text-[11px] font-semibold tracking-wide">
                [TOOL CALL] ➔ ${toolName}
            </div>
            <div class="text-amber-300/70 font-mono text-[11px] bg-amber-950/20 p-2 rounded border border-amber-900/20 overflow-x-auto">
                Parametreler: ${JSON.stringify(inputs, null, 2)}
            </div>
            <div class="tool-output-container"></div>
        </div>`;

    wrapper.innerHTML = `${logoHTML}${contentHTML}`;
    terminal.appendChild(wrapper);
    terminal.scrollTop = terminal.scrollHeight;
    
    return wrapper; // Güncelleyebilmek için element referansını dönüyoruz
}

function updateToolResultLog(wrapper, outputText, isError = false) {
    const logo = wrapper.querySelector('.tool-logo');
    const outputContainer = wrapper.querySelector('.tool-output-container');
    
    if (!outputContainer) return;

    // Çıktı alanını oluştur
    const outputDiv = document.createElement('div');
    outputDiv.className = "mt-2 pt-2 border-t border-amber-900/20";
    
    if (isError) {
        // HATA DURUMU: Logoyu kırmızı yap ve içeriği kırmızı bas
        logo.className = "tool-logo flex-shrink-0 w-7 h-7 rounded-full bg-red-500/10 border border-red-500/40 flex items-center justify-center text-red-400 text-xs transition-colors duration-300";
        outputDiv.innerHTML = `
            <div class="text-red-400 font-mono text-[11px] font-semibold">[TOOL ERROR]</div>
            <pre class="text-red-300/80 font-mono text-[11px] whitespace-pre-wrap mt-1">${outputText}</pre>
        `;
    } else {
        // BAŞARILI DURUM: Logoyu yeşil yap ve içeriği standart terminal çıktısı olarak bas (Tik işareti yok)
        logo.className = "tool-logo flex-shrink-0 w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-emerald-400 text-xs transition-colors duration-300";
        outputDiv.innerHTML = `
            <div class="text-zinc-400 font-mono text-[11px] font-semibold">[TOOL OUTPUT]</div>
            <pre class="text-zinc-400 font-mono text-[11px] whitespace-pre-wrap mt-1 bg-zinc-900/30 p-2 rounded border border-zinc-800/50">${outputText}</pre>
        `;
    }

    outputContainer.appendChild(outputDiv);
    
    // Terminali en alta kaydır
    const terminal = document.getElementById('terminal');
    terminal.scrollTop = terminal.scrollHeight;
}

// Görevi Sonlandırma ve UI'ı eski haline getirme
function endTask(status) {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    const statusBadge = document.getElementById('status-badge');
    const runBtn = document.getElementById('run-btn');

    if (status === "Success") {
        statusBadge.innerText = "Status: Idle (Done)";
        statusBadge.className = "text-xs font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-900/50 px-3 py-1 rounded-full";
    } else {
        statusBadge.innerText = `Status: ${status}`;
        statusBadge.className = "text-xs font-mono text-red-400 bg-red-950/30 border border-red-900/50 px-3 py-1 rounded-full";
    }

    runBtn.disabled = false;
    runBtn.classList.remove('opacity-50', 'cursor-not-allowed');
}

// Terminale Log Ekleme Fonksiyonu
function appendLog(type, text) {
    const terminal = document.getElementById('terminal');
    if (!terminal) return;

    const wrapper = document.createElement('div');
    wrapper.className = "flex w-full my-3 animate-fade-in items-start gap-3";
    
    let logoHTML = "";
    let contentClass = "";
    let customStyle = "";

    switch (type) {
        case 'user':
            wrapper.classList.add("justify-start", "flex-row-reverse");
            logoHTML = `
                <div class="flex-shrink-0 w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono text-[${logoTextSize}px] font-bold">
                    U
                </div>`;
            contentClass = `bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl text-blue-200/90 whitespace-pre-wrap max-w-[70%] text-[${contentTextSize}px] w-auto`;
            break;

        case 'tool_call':
            wrapper.classList.add("justify-start");
            logoHTML = `
                <div class="flex-shrink-0 w-7 h-7 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-mono text-[${logoTextSize}px] font-bold">
                    ⚙️
                </div>`;
            contentClass = `bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl text-blue-200/90 whitespace-pre-wrap max-w-[70%] text-[${contentTextSize}px] w-auto`;
            customStyle = `font-size:${contentTextSize*TOOL_FONT_RATIO}px;`;
            break;

        case 'tool_result':
            wrapper.classList.add("justify-start");
            logoHTML = `
                <div class="flex-shrink-0 w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs">
                    ✓
                </div>`;
            contentClass = `bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl text-blue-200/90 whitespace-pre-wrap max-w-[70%] text-[${contentTextSize}px] w-auto`;
            customStyle = `font-size:${contentTextSize*TOOL_FONT_RATIO}px;`;
            break;

        case 'final_answer':
            wrapper.classList.add("justify-start");
            logoHTML = `
                <div class="flex-shrink-0 w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-mono text-[${logoTextSize}px] font-bold">
                    AI
                </div>`;
            contentClass = `bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl text-blue-200/90 whitespace-pre-wrap max-w-[70%] text-[${contentTextSize}px] w-auto`;
            break;

        case 'error':
            wrapper.classList.add("justify-start");
            logoHTML = `
                <div class="flex-shrink-0 w-7 h-7 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 text-xs font-bold">
                    ✕
                </div>`;
            contentClass = `bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl text-blue-200/90 whitespace-pre-wrap max-w-[70%] text-[${contentTextSize}px] w-auto`;
            break;

        case 'usage':
            wrapper.className = "flex justify-center my-1 w-full text-center";
            logoHTML = "";
            contentClass = "text-indigo-400/80 text-[11px] font-mono";
            break;

        case 'system':
            wrapper.className = "flex justify-center my-2 w-full text-center";
            logoHTML = "";
            contentClass = "text-zinc-600 font-mono text-xs max-w-3xl border border-zinc-800/40 bg-zinc-900/20 px-3 py-1.5 rounded-md";
            break;

        default:
            wrapper.className = "flex justify-center my-1 w-full text-center";
            logoHTML = "";
            contentClass = "text-zinc-500 text-[11px] font-mono";
    }

    wrapper.innerHTML = `${logoHTML}<div class="${contentClass}" style="${customStyle}"></div>`;
    
    wrapper.querySelector('div:last-child').innerText = text;
    
    terminal.appendChild(wrapper);
    terminal.scrollTop = terminal.scrollHeight;
}