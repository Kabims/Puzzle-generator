"""
Modul 2: Puzzle Solver Otomatis (Berbasis Pengolahan Citra Digital)
Bertugas merangkai 1 citra bingkai dan N potongan citra menjadi sebuah gambar utuh
tanpa bergantung pada kunci_jawaban.json.
"""
import numpy as np


def deteksi_area_bingkai(frame, pieces):
    """
    Mendeteksi koordinat area kosong (x0, y0, x1, y1) pada bingkai
    hanya berbekal citra bingkai dan kumpulan potongan.
    """
    H, W = frame.shape[:2]
    total_area = sum(p.shape[0] * p.shape[1] for p in pieces)

    # 1. Cari area putih (255) simetris yang luas pikselnya sama persis dengan jumlah luas N potongan
    kandidat = []
    for my in range(1, H // 2):
        h_hole = H - 2 * my
        if total_area % h_hole != 0:
            continue
        w_hole = total_area // h_hole
        if (W - w_hole) % 2 != 0 or w_hole <= 0 or w_hole >= W:
            continue
        mx = (W - w_hole) // 2
        x0, y0, x1, y1 = mx, my, W - mx, H - my
        if np.all(frame[y0:y1, x0:x1] == 255):
            diff_ratio = abs((mx / W) - (my / H))
            kandidat.append((diff_ratio, dict(x0=int(x0), y0=int(y0), x1=int(x1), y1=int(y1))))

    if kandidat:
        kandidat.sort(key=lambda x: x[0])
        return kandidat[0][1]

    # 2. Fallback: ekspansi area putih dari titik tengah bingkai
    is_white = np.all(frame == 255, axis=-1) if frame.ndim == 3 else (frame == 255)
    cy, cx = H // 2, W // 2
    y0, y1 = cy, cy
    while y0 > 0 and is_white[y0 - 1, cx]:
        y0 -= 1
    while y1 < H and is_white[y1, cx]:
        y1 += 1
    x0, x1 = cx, cx
    while x0 > 0 and is_white[cy, x0 - 1]:
        x0 -= 1
    while x1 < W and is_white[cy, x1]:
        x1 += 1
    return dict(x0=int(x0), y0=int(y0), x1=int(x1), y1=int(y1))


def biaya_tepi(e1, e1_in, e2, e2_in):
    """
    Mengukur ketidakcocokan (dissimilarity) antara dua tepi citra menggunakan 3 fitur PCD:
    1. Kontinuitas Warna/Intensitas Piksel Langsung (L1 Distance)
    2. Kontinuitas Gradien Normal (Ekstrapolasi Turunan Orde-1 Lintas Batas)
    3. Kemiripan Profil Gradien Tangensial (Kontur Sepanjang Tepi Batas)
    """
    if e1.shape != e2.shape:
        return 1e6
    e1 = e1.astype(np.float32)
    e1_in = e1_in.astype(np.float32)
    e2 = e2.astype(np.float32)
    e2_in = e2_in.astype(np.float32)

    # 1. Selisih nilai piksel langsung di perbatasan
    diff_color = np.mean(np.abs(e1 - e2))

    # 2. Ekstrapolasi gradien normal: memprediksi piksel seberang dari kemiringan lokal
    pred_e2 = np.clip(2.0 * e1 - e1_in, 0.0, 255.0)
    pred_e1 = np.clip(2.0 * e2 - e2_in, 0.0, 255.0)
    diff_grad_norm = 0.5 * (np.mean(np.abs(e2 - pred_e2)) + np.mean(np.abs(e1 - pred_e1)))

    # 3. Selisih turunan tangensial sepanjang garis batas
    if e1.shape[0] > 1:
        tan1 = e1[1:] - e1[:-1]
        tan2 = e2[1:] - e2[:-1]
        diff_grad_tan = np.mean(np.abs(tan1 - tan2))
    else:
        diff_grad_tan = 0.0

    return float(1.0 * diff_color + 0.6 * diff_grad_norm + 0.5 * diff_grad_tan)


def ekstrak_tepi_potongan(img):
    """Mengekstrak 4 sisi tepi (top, bottom, left, right) beserta baris/kolom piksel dalamnya."""
    return {
        "top":    (img[0, :],  img[min(1, img.shape[0] - 1), :]),
        "bottom": (img[-1, :], img[max(0, img.shape[0] - 2), :]),
        "left":   (img[:, 0],  img[:, min(1, img.shape[1] - 1)]),
        "right":  (img[:, -1], img[:, max(0, img.shape[1] - 2)]),
    }


def solve_puzzle(frame, pieces):
    """
    Merangkai 1 citra bingkai dan N potongan citra menjadi gambar utuh secara otomatis.
    Mendukung potongan yang telah diacak urutannya maupun dirotasi (0/90/180/270 derajat).
    Mengembalikan: (hasil_citra, board, detail_susunan, area)
    """
    N = len(pieces)
    M = int(round(np.sqrt(N)))
    if M * M != N:
        raise ValueError(
            f"Jumlah potongan ({N}) harus merupakan bilangan kuadrat sempurna (M × M), misal 4, 9, 16, 25."
        )

    area = deteksi_area_bingkai(frame, pieces)
    x0, y0, x1, y1 = area["x0"], area["y0"], area["x1"], area["y1"]

    ys = np.linspace(y0, y1, M + 1).astype(int)
    xs = np.linspace(x0, x1, M + 1).astype(int)

    # Siapkan 4 kemungkinan orientasi rotasi (0, 90, 180, 270 CCW) untuk setiap potongan
    rot_imgs = {}
    rot_edges = {}
    for i, p in enumerate(pieces):
        for k in range(4):
            im = np.rot90(p, k) if k else p
            rot_imgs[(i, k)] = im
            rot_edges[(i, k)] = ekstrak_tepi_potongan(im)

    # Ekstrak tepi dalam dari bingkai sebagai acuan slot pinggir
    frame_edges = {}
    for r in range(M):
        for c in range(M):
            fe = {}
            if r == 0 and y0 > 0:
                fe["top"] = (frame[y0 - 1, xs[c]:xs[c + 1]], frame[max(0, y0 - 2), xs[c]:xs[c + 1]])
            if r == M - 1 and y1 < frame.shape[0]:
                fe["bottom"] = (frame[y1, xs[c]:xs[c + 1]], frame[min(frame.shape[0] - 1, y1 + 1), xs[c]:xs[c + 1]])
            if c == 0 and x0 > 0:
                fe["left"] = (frame[ys[r]:ys[r + 1], x0 - 1], frame[ys[r]:ys[r + 1], max(0, x0 - 2)])
            if c == M - 1 and x1 < frame.shape[1]:
                fe["right"] = (frame[ys[r]:ys[r + 1], x1], frame[ys[r]:ys[r + 1], min(frame.shape[1] - 1, x1 + 1)])
            frame_edges[(r, c)] = fe

    cache_frame_cost = {}
    cache_pair_cost = {}

    def get_frame_cost(i, k, r, c):
        key = (i, k, r, c)
        if key not in cache_frame_cost:
            edges = rot_edges[(i, k)]
            fe = frame_edges[(r, c)]
            c_val = 0.0
            cnt = 0
            for side in ("top", "bottom", "left", "right"):
                if side in fe:
                    c_val += 1.25 * biaya_tepi(edges[side][0], edges[side][1], fe[side][0], fe[side][1])
                    cnt += 1
            cache_frame_cost[key] = (c_val, cnt)
        return cache_frame_cost[key]

    def get_pair_cost(i1, k1, side1, i2, k2, side2):
        key = (i1, k1, side1, i2, k2, side2)
        if key not in cache_pair_cost:
            e1 = rot_edges[(i1, k1)][side1]
            e2 = rot_edges[(i2, k2)][side2]
            cache_pair_cost[key] = biaya_tepi(e1[0], e1[1], e2[0], e2[1])
        return cache_pair_cost[key]

    def ukuran_cocok(i, k, r, c):
        sh, sw = ys[r + 1] - ys[r], xs[c + 1] - xs[c]
        ph, pw = rot_imgs[(i, k)].shape[:2]
        return ph == sh and pw == sw

    def hitung_biaya_slot(i, k, r, c, board):
        f_cost, cnt = get_frame_cost(i, k, r, c)
        total = f_cost
        if r > 0 and (r - 1, c) in board:
            ni, nk = board[(r - 1, c)]
            total += get_pair_cost(i, k, "top", ni, nk, "bottom")
            cnt += 1
        if r < M - 1 and (r + 1, c) in board:
            ni, nk = board[(r + 1, c)]
            total += get_pair_cost(i, k, "bottom", ni, nk, "top")
            cnt += 1
        if c > 0 and (r, c - 1) in board:
            ni, nk = board[(r, c - 1)]
            total += get_pair_cost(i, k, "left", ni, nk, "right")
            cnt += 1
        if c < M - 1 and (r, c + 1) in board:
            ni, nk = board[(r, c + 1)]
            total += get_pair_cost(i, k, "right", ni, nk, "left")
            cnt += 1
        if cnt == 0:
            return float("inf"), 0
        return total / cnt, cnt

    # Fase 1: Best-First Priority Greedy dari pinggir bingkai menuju ke tengah
    board = {}
    terpakai = set()

    for _ in range(N):
        kandidat_langkah = []
        slot_kosong = [(r, c) for r in range(M) for c in range(M) if (r, c) not in board]

        for (r, c) in slot_kosong:
            skor_kandidat = []
            jml_ref = 0
            for i in range(N):
                if i in terpakai:
                    continue
                for k in range(4):
                    if not ukuran_cocok(i, k, r, c):
                        continue
                    cost, n_ref = hitung_biaya_slot(i, k, r, c, board)
                    if n_ref > 0:
                        jml_ref = n_ref
                        skor_kandidat.append((cost, i, k))

            if skor_kandidat:
                skor_kandidat.sort(key=lambda x: x[0])
                best_cost, best_i, best_k = skor_kandidat[0]
                second_cost = skor_kandidat[1][0] if len(skor_kandidat) > 1 else best_cost + 100.0
                ratio = (best_cost + 1e-3) / (second_cost + 1e-3)
                kandidat_langkah.append((-jml_ref, ratio, best_cost, r, c, best_i, best_k))

        kandidat_langkah.sort()
        _, _, _, br, bc, bi, bk = kandidat_langkah[0]
        board[(br, bc)] = (bi, bk)
        terpakai.add(bi)

    # Fase 2: Global Refinement (2-Opt Swap & Optimasi Rotasi)
    def total_global_cost(b):
        total = 0.0
        for r in range(M):
            for c in range(M):
                i, k = b[(r, c)]
                total += get_frame_cost(i, k, r, c)[0]
                if r < M - 1:
                    ni, nk = b[(r + 1, c)]
                    total += get_pair_cost(i, k, "bottom", ni, nk, "top")
                if c < M - 1:
                    ni, nk = b[(r, c + 1)]
                    total += get_pair_cost(i, k, "right", ni, nk, "left")
        return total

    improved = True
    iter_count = 0
    cur_cost = total_global_cost(board)
    slots = [(r, c) for r in range(M) for c in range(M)]

    while improved and iter_count < 15:
        improved = False
        iter_count += 1

        for (r, c) in slots:
            i, cur_k = board[(r, c)]
            for k in range(4):
                if k != cur_k and ukuran_cocok(i, k, r, c):
                    board[(r, c)] = (i, k)
                    new_cost = total_global_cost(board)
                    if new_cost < cur_cost - 1e-4:
                        cur_cost = new_cost
                        cur_k = k
                        improved = True
                    else:
                        board[(r, c)] = (i, cur_k)

        for idx1 in range(N):
            for idx2 in range(idx1 + 1, N):
                s1, s2 = slots[idx1], slots[idx2]
                i1, k1 = board[s1]
                i2, k2 = board[s2]
                best_pair = None
                for nk1 in range(4):
                    if not ukuran_cocok(i2, nk1, s1[0], s1[1]):
                        continue
                    for nk2 in range(4):
                        if not ukuran_cocok(i1, nk2, s2[0], s2[1]):
                            continue
                        board[s1] = (i2, nk1)
                        board[s2] = (i1, nk2)
                        new_cost = total_global_cost(board)
                        if new_cost < cur_cost - 1e-4:
                            cur_cost = new_cost
                            best_pair = (nk1, nk2)
                if best_pair is not None:
                    board[s1] = (i2, best_pair[0])
                    board[s2] = (i1, best_pair[1])
                    improved = True
                else:
                    board[s1] = (i1, k1)
                    board[s2] = (i2, k2)

    # Rangkai menjadi citra utuh
    hasil_citra = frame.copy()
    detail_susunan = []
    for r in range(M):
        for c in range(M):
            i, k = board[(r, c)]
            hasil_citra[ys[r]:ys[r + 1], xs[c]:xs[c + 1]] = rot_imgs[(i, k)]
            detail_susunan.append({
                "slot": r * M + c,
                "baris": r,
                "kolom": c,
                "idx_potongan": i,
                "putar_ccw": k,
                "derajat_putar": k * 90
            })

    return hasil_citra, board, detail_susunan, area
