"""
Modul 1: Puzzle Generator
Bertugas membaca citra masukan, membuat bingkai (frame), memotong area kosong
menjadi M x M potongan, melakukan rotasi/pengacakan, dan menyimpan output.
"""

import os
import glob
import random
import numpy as np
from PIL import Image

def buat_bingkai(arr_img, margin_rasio=0.07):
    """Memutihkan bagian tengah gambar agar terbentuk bingkai"""
    Height, Width = arr_img.shape[:2]
    margin_x = int(round(Width * margin_rasio))
    margin_y = int(round(Height * margin_rasio))
    frame = arr_img.copy()
    frame[margin_y:Height - margin_y, margin_x:Width - margin_x] = 255
    area = dict(kiri=margin_x, atas=margin_y, kanan=Width - margin_x, bawah=Height - margin_y)
    return frame, area

def potong_grid(arr_img, M, area):
    """Memotong bagian tengah dan dibagi menjadi M x M potongan."""
    kiri, atas, kanan, bawah = area["kiri"], area["atas"], area["kanan"], area["bawah"]
    garis_vertikal = np.linspace(atas, bawah, M + 1).astype(int)
    garis_horizontal = np.linspace(kiri, kanan, M + 1).astype(int)
    pieces = []
    for row in range(M):
        for col in range(M):
            piece = arr_img[garis_vertikal[row]:garis_vertikal[row + 1], garis_horizontal[col]:garis_horizontal[col + 1]].copy()
            pieces.append(piece)
    return pieces

def buat_puzzle(img_pil, M=4, margin_rasio=0.07, rotasi_acak=True, acak_urutan=True, out_dir="output"):
    """
    Memproses citra masukan menjadi bingkai & N potongan puzzle,
    menyimpan hasil, dan mengembalikan: (frame, pot_list, info)
    """
    if img_pil.mode not in ("RGB", "L"):
        img_pil = img_pil.convert("RGB")

    arr_img = np.array(img_pil)
    Height, Width = arr_img.shape[:2]
    N = M * M

    frame, area = buat_bingkai(arr_img, margin_rasio)
    pieces = potong_grid(arr_img, M, area)

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
        piece = pieces[idx]
        nama = f"piece_{nomor:02d}.png"
        Image.fromarray(piece).save(os.path.join(pieces_dir, nama))
        pot_list.append(piece)
        nama_files.append(nama)

    info = {
        "M": M,
        "ukuran_asli": [Width, Height],
        "mode": img_pil.mode,
        "nama_files": nama_files,
    }

    return frame, pot_list, info