# わたしがデータ整列のために用意したファイル

import pathlib

# 1. パスの設定
wav_dir = pathlib.Path("../downloads/ver20221208/speech")
txt_dir = pathlib.Path("../downloads/ver20221208/transcript/utf-8")

# 2. 書き出し用ファイルのオープン
with open("wav.scp", "w") as f_wav, open("text", "w") as f_txt, open("utt2spk", "w") as f_u2s:
    
    # 3. wavファイルを一つずつ処理
    for wav_path in sorted(wav_dir.glob("**/*.wav")):
        # ファイル名からIDを作成
        tape_id = wav_path.parent.name
        file_id = wav_path.stem
        utt_id = f"tohoku_{tape_id}_{file_id}"
        
        # 4. 対応するテキストを取得
        rel_path = wav_path.relative_to(wav_dir).with_suffix(".txt")
        target_txt = txt_dir / rel_path
        
        if target_txt.exists():
            content = target_txt.read_text(encoding="utf-8").strip()
            
            # 5. 各ファイルに書き込み
            f_wav.write(f"{utt_id} {wav_path.absolute()}\n")
            f_txt.write(f"{utt_id} {content}\n")
            f_u2s.write(f"{utt_id} {tape_id}\n") # 仮にテープ単位を話者とする場合