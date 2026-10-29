#!/usr/bin/env python3
"""
AVI to MP3 Ultra-Fast Parallel Converter
Converte múltiplos arquivos .avi para .mp3 simultaneamente utilizando
pool de threads, modo rápido do libmp3lame e leitura otimizada de diretórios.
"""

import argparse
import concurrent.futures
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# Lock para sincronização de saída visual no terminal
print_lock = threading.Lock()


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configura o logger estruturado para o terminal."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%H:%M:%S"
    
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    return logging.getLogger("avi_to_mp3")


def find_ffmpeg(custom_path: Optional[str] = None) -> str:
    """Localiza o executável FFmpeg no PATH ou caminho indicado."""
    if custom_path:
        path = shutil.which(custom_path) or (custom_path if os.path.isfile(custom_path) else None)
        if not path:
            raise FileNotFoundError(f"FFmpeg não encontrado no caminho fornecido: {custom_path}")
        return path

    path = shutil.which("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "FFmpeg não foi encontrado no PATH do sistema. "
            "Certifique-se de que o FFmpeg está instalado."
        )
    return path


def validate_bitrate(bitrate: str) -> str:
    """Valida a formatação de taxa de bits."""
    bitrate = bitrate.strip().lower()
    val = bitrate[:-1] if bitrate.endswith("k") else bitrate
    if not val.isdigit() or int(val) <= 0:
        raise ValueError(f"Bitrate inválido: '{bitrate}'. Formato esperado: '128k', '192k', '320k'.")
    return bitrate if bitrate.endswith("k") else f"{bitrate}k"


def select_folder_dialog(title: str, initial_dir: Optional[str] = None) -> Optional[str]:
    """Abre caixa de diálogo do Windows para escolha de diretório."""
    if not HAS_TKINTER:
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title=title, initialdir=initial_dir)
        root.destroy()
        return folder if folder else None
    except Exception:
        return None


def prompt_user_paths() -> Tuple[Path, Path]:
    """Solicita interativamente origem e destino."""
    print("=" * 65, flush=True)
    print("   CONVERSOR ULTRA-RÁPIDO (MULTI-CORE PARALELO) AVI -> MP3", flush=True)
    print("=" * 65, flush=True)
    print("\n[Passo 1/2] Selecione a pasta onde estão os arquivos .avi...", flush=True)

    src = select_folder_dialog("Selecione a pasta de ORIGEM (com os vídeos .avi)")
    if not src:
        src_raw = input("Ou digite o caminho da pasta de origem (ex: F:\\): ").strip().strip('"').strip("'")
        src = src_raw

    if not src:
        raise ValueError("Nenhuma pasta de origem foi indicada. Processo cancelado.")

    desktop_default = Path.home() / "Desktop" / "teste"
    print(f"\n[Passo 2/2] Selecione a pasta de DESTINO (Padrão: {desktop_default})...", flush=True)

    dest = select_folder_dialog("Selecione a pasta de DESTINO (onde salvar os .mp3)", str(desktop_default.parent))
    if not dest:
        dest_raw = input(f"Ou digite o destino [Pressione Enter para '{desktop_default}']: ").strip().strip('"').strip("'")
        dest = dest_raw if dest_raw else str(desktop_default)

    return Path(src).resolve(), Path(dest).resolve()


def convert_worker(
    ffmpeg_bin: str,
    input_file: Path,
    output_file: Path,
    bitrate: str,
    sample_rate: int,
    channels: int,
    overwrite: bool,
    delete_source: bool,
    progress_state: dict,
    total_files: int,
) -> bool:
    """
    Worker paralelo: executa a extração no modo de alta velocidade do LAME.
    """
    if not input_file.is_file():
        return False

    if output_file.exists() and not overwrite:
        with print_lock:
            progress_state["completed"] += 1
            print(f"[{progress_state['completed']}/{total_files}] [PULADO] Já existe: {output_file.name}", flush=True)
        return True

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Parâmetros de aceleração máxima:
    # -map 0:a:0? -> decodifica apenas o stream de áudio, descartando buffers de vídeo
    # -compression_level 0 -> algoritmo mais rápido do libmp3lame (zero overhead de análise)
    # -threads 0 -> alocação dinâmica de threads
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel", "error",
        "-y" if overwrite else "-n",
        "-i", str(input_file),
        "-vn",
        "-map", "0:a:0?",
        "-c:a", "libmp3lame",
        "-compression_level", "0",
        "-b:a", bitrate,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-threads", "0",
        str(output_file),
    ]

    t0 = time.time()
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        elapsed = time.time() - t0

        if res.returncode != 0:
            with print_lock:
                progress_state["completed"] += 1
                print(f"[{progress_state['completed']}/{total_files}] [ERRO] {input_file.name}: {res.stderr.strip()}", flush=True)
            if output_file.exists() and output_file.stat().st_size == 0:
                output_file.unlink(missing_ok=True)
            return False

        if not output_file.exists() or output_file.stat().st_size == 0:
            return False

        if delete_source:
            input_file.unlink()

        out_mb = output_file.stat().st_size / (1024 * 1024)
        with print_lock:
            progress_state["completed"] += 1
            progress_state["success"] += 1
            pct = (progress_state["completed"] / total_files) * 100
            print(
                f"[{progress_state['completed']}/{total_files} - {pct:.0f}%] "
                f"✓ {output_file.name} ({out_mb:.1f} MB em {elapsed:.1f}s)",
                flush=True,
            )

        return True

    except Exception as exc:
        with print_lock:
            progress_state["completed"] += 1
            print(f"[{progress_state['completed']}/{total_files}] [FALHA] {input_file.name}: {exc}", flush=True)
        return False


def build_task_list(input_root: Path, output_root: Path) -> List[Tuple[Path, Path]]:
    """Localiza todos os arquivos .avi recursivamente."""
    tasks: List[Tuple[Path, Path]] = []

    if input_root.is_file():
        if input_root.suffix.lower() != ".avi":
            raise ValueError(f"O arquivo não é .avi: {input_root}")
        dest = output_root / f"{input_root.stem}.mp3" if output_root.is_dir() else output_root
        tasks.append((input_root, dest))
        return tasks

    if not input_root.is_dir():
        raise FileNotFoundError(f"Diretório não encontrado: {input_root}")

    print(f"\n🔍 Mapeando pastas em '{input_root}'...", end="", flush=True)
    found_files: List[Path] = []
    for root_dir, _, files in os.walk(str(input_root)):
        for f in files:
            if f.lower().endswith(".avi"):
                found_files.append(Path(root_dir) / f)

    print(f" Concluído! ({len(found_files)} arquivos encontrados)", flush=True)

    if not found_files:
        raise FileNotFoundError(f"Nenhum arquivo .avi encontrado em: {input_root}")

    for src in sorted(found_files):
        rel_path = src.relative_to(input_root)
        dest = output_root / rel_path.with_suffix(".mp3")
        tasks.append((src, dest))

    return tasks


def parse_arguments() -> argparse.Namespace:
    """Configura argumentos CLI."""
    parser = argparse.ArgumentParser(description="Conversor Paralelo AVI para MP3.")
    parser.add_argument("-i", "--input", default=None, help="Diretório de origem.")
    parser.add_argument("-o", "--output", default=None, help="Diretório de destino.")
    parser.add_argument("-b", "--bitrate", default="192k", help="Taxa de bits (padrão: 192k).")
    parser.add_argument("-w", "--workers", default=None, type=int, help="Número de conversões simultâneas (padrão: núcleos da CPU).")
    parser.add_argument("-r", "--sample-rate", default=44100, type=int, help="Sample rate (Hz).")
    parser.add_argument("-c", "--channels", default=2, type=int, help="Canais (1 mono, 2 estéreo).")
    parser.add_argument("-y", "--overwrite", action="store_true", help="Sobrescrever existentes.")
    parser.add_argument("--delete-source", action="store_true", help="Apagar .avi de origem após conversão.")
    parser.add_argument("--ffmpeg-path", default=None, help="Caminho do executável ffmpeg.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Modo verboso.")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    logger = setup_logger(verbose=args.verbose)
    interactive = args.input is None

    try:
        ffmpeg_bin = find_ffmpeg(args.ffmpeg_path)

        if interactive:
            input_root, output_root = prompt_user_paths()
            overwrite = True
        else:
            input_root = Path(args.input).resolve()
            output_root = Path(args.output).resolve() if args.output else input_root
            overwrite = args.overwrite

        bitrate = validate_bitrate(args.bitrate)
        tasks = build_task_list(input_root=input_root, output_root=output_root)
        total_files = len(tasks)

        # Determina o número de conversões paralelas (CPU threads)
        cpu_count = os.cpu_count() or 4
        workers = args.workers if args.workers else max(2, min(cpu_count, 8))

        print("\n" + "=" * 65, flush=True)
        print(f" PIPELINE ATIVADO: {total_files} vídeos na fila", flush=True)
        print(f" Processamento Paralelo: {workers} arquivos convertidos AO MESMO TEMPO", flush=True)
        print(f" Encoder: libmp3lame (Fast Mode) | Bitrate: {bitrate}", flush=True)
        print("=" * 65 + "\n", flush=True)

        progress_state = {"completed": 0, "success": 0}
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    convert_worker,
                    ffmpeg_bin=ffmpeg_bin,
                    input_file=src,
                    output_file=dest,
                    bitrate=bitrate,
                    sample_rate=args.sample_rate,
                    channels=args.channels,
                    overwrite=overwrite,
                    delete_source=args.delete_source,
                    progress_state=progress_state,
                    total_files=total_files,
                )
                for src, dest in tasks
            ]
            concurrent.futures.wait(futures)

        elapsed_total = time.time() - start_time
        success = progress_state["success"]

        print("\n" + "=" * 65, flush=True)
        print(" RESULTADO FINAL:", flush=True)
        print(f" Sucessos: {success}/{total_files} arquivos convertidos", flush=True)
        print(f" Tempo Total: {elapsed_total:.1f} segundos ({elapsed_total / 60:.2f} minutos)", flush=True)
        print(f" Arquivos salvos em: {output_root}", flush=True)
        print("=" * 65, flush=True)

        return 0 if success == total_files else 1

    except Exception as err:
        print(f"\n[ERRO FATAL] {err}", flush=True)
        return 1

    finally:
        if interactive:
            input("\nPressione ENTER para encerrar...")


if __name__ == "__main__":
    sys.exit(main())