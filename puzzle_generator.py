"""
Modul 1: Puzzle Generator
Bertugas membaca citra masukan, membuat bingkai (frame), memotong area kosong
menjadi M x M potongan, melakukan rotasi/pengacakan opsional, dan menyimpan keluaran.
"""
import os
import glob
import random
import numpy as np
from PIL import Image


def buat_bingkai(arr, margin_rasio=0.07):
    """Membuat citra bingkai dengan bagian tengah dikosongkan (putih = 255)."""
    H, W = arr.shape[:2]
    mx, my = int(round(W * margin_rasio)), int(round(H * margin_rasio))
    frame = arr.copy()
    frame[my:H - my, mx:W - mx] = 255
    area = dict(x0=mx, y0=my, x1=W - mx, y1=H - my)
    return frame, area


def potong_grid(arr, M, area):
    """Memotong area kosong pada bingkai menjadi M x M potongan."""
    x0, y0, x1, y1 = area["x0"], area["y0"], area["x1"], area["y1"]
    ys = np.linspace(y0, y1, M + 1).astype(int)
    xs = np.linspace(x0, x1, M + 1).astype(int)
    pieces = []
    for r in range(M):
        for c in range(M):
            p = arr[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].copy()
            pieces.append(p)
    return pieces


def buat_puzzle(img_pil, M=4, margin_rasio=0.07, rotasi_acak=True, acak_urutan=True, out_dir="output"):
    """
    Memproses citra masukan menjadi bingkai & N potongan puzzle,
    menyimpan hasilnya ke folder `out_dir` (tanpa menyimpan kunci jawaban),
    serta mengembalikan: (arr_asli, frame, pot_list, info)
    """
    if img_pil.mode not in ("RGB", "L"):
        img_pil = img_pil.convert("RGB")

    arr = np.array(img_pil)
    H, W = arr.shape[:2]
    N = M * M

    frame, area = buat_bingkai(arr, margin_rasio)
    pieces = potong_grid(arr, M, area)

    for i in range(len(pieces)):
        k = random.randint(0, 3) if rotasi_acak else 0
        if k:
            pieces[i] = np.rot90(pieces[i], k).copy()

    urutan = list(range(N))
    if acak_urutan:
        random.shuffle(urutan)

    pieces_dir = os.path.join(out_dir, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)
    for old_file in glob.glob(os.path.join(pieces_dir, "piece_*.png")):
        try:
            os.remove(old_file)
        except OSError:
            pass

    Image.fromarray(frame).save(os.path.join(out_dir, "frame.png"))

    pot_list = []
    nama_files = []

    for nomor, idx in enumerate(urutan):
        p = pieces[idx]
        nama = f"piece_{nomor:02d}.png"
        Image.fromarray(p).save(os.path.join(pieces_dir, nama))
        pot_list.append(p)
        nama_files.append(nama)

    info = {
        "M": M,
        "ukuran_asli": [W, H],
        "mode": img_pil.mode,
        "area_bingkai": area,
        "nama_files": nama_files,
    }

    return arr, frame, pot_list, info

