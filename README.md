# AVI to MP3 Audio Extractor & Tree Mirror

Um utilitário de alta performance em Python para extração de áudio de vídeos `.avi` para `.mp3`, com suporte a espelhamento idêntico de árvores de diretórios, execução paralela multi-core e interface interativa nativa.

---

## ⚡ Recursos Principais

- **Espelhamento Recursivo de Diretórios:** Mapeia toda a hierarquia de pastas e subpastas da origem e recria a mesma estrutura no destino, renomeando apenas os arquivos para `.mp3`.
- **Modo Interativo Visual:** Ao executar via duplo clique, abre caixas de diálogo nativas do Windows para seleção das pastas de entrada e saída.
- **Processamento Concorrente Multi-Core:** Pool paralelo de *workers* (`ThreadPoolExecutor`) que processa múltiplos arquivos simultaneamente, saturando todos os núcleos da CPU.
- **Otimização de Codificação:** Configurações de alta velocidade com o codificador `libmp3lame` (`-compression_level 0`) e isolamento de stream (`-map 0:a:0?`), evitando decodificação desnecessária de quadros de vídeo.
- **Telemetria e Tolerância a Falhas:** Logs em tempo real com contagem de progresso, percentual, tempo decorrido e tamanho final. Caso um arquivo esteja corrompido, a fila continua sem interrupção.
- **Limpeza Opcional de Disco:** Flag para remoção automática do arquivo `.avi` original após a integridade do `.mp3` ser validada.

---

## 🛠️ Pré-requisitos

1. **Python 3.8+** instalado no sistema.
2. **FFmpeg** instalado e adicionado às variáveis de ambiente (PATH).
   - No Windows via terminal:
     ```powershell
     winget install Gyan.FFmpeg
     ```
   - No Linux (Debian/Ubuntu):
     ```bash
     sudo apt update && sudo apt install ffmpeg
     ```

---

## 🚀 Como Usar

### 1. Modo Interativo (Interface Visual)
Dê um **duplo clique** no arquivo `conversor.py` ou execute sem parâmetros no terminal:
```powershell
python conversor.py


### 2. Modo Linha de Comando (CLI)
Converter mantendo a estrutura de pastas do pendrive para o Desktop:
powershell


python conversor.py -i "F:\" -o "C:\Users\Usuario\Desktop\Audios"
Converter com taxa de bits customizada (320 kbps) e 8 threads simultâneas:
powershell


python conversor.py -i "C:\Videos" -o "C:\Audios" -b 320k -w 8
Converter e remover os arquivos .avi originais para liberar espaço:
powershell


python conversor.py -i "F:\" --delete-source
