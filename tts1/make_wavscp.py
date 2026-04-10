import os
import sys
import glob
import subprocess
import numpy as np
from sklearn.model_selection import train_test_split

np.random.seed(seed=32)

def sort_file(fname):
    """Kaldi/ESPnet必須のLC_ALL=Cソート"""
    subprocess.call(f'export LC_ALL=C; sort "{fname}" > "{fname}.sorted"', shell=True)
    subprocess.call(f'rm "{fname}"', shell=True)
    subprocess.call(f'mv "{fname}.sorted" "{fname}"', shell=True)

def make_wavscp(wav_paths, out_dir):
    """
    wav.scpを作成: 形式 -> FILE_ID ABSOLUTE_PATH_TO_WAV
    """
    os.makedirs(out_dir, exist_ok=True)
    out_fname = os.path.join(out_dir, 'wav.scp')
    
    with open(out_fname, 'w', encoding='utf-8') as out:
        for wav_path in wav_paths:
            # パスからテープ名とファイル名を抽出 (例: tape001 と 00_吉野の石落し.wav)
            tape_dir_name = os.path.basename(os.path.dirname(wav_path))
            fname = os.path.basename(wav_path)
            
            # KaldiのIDとして「テープ名_ファイル名」を使用
            file_id_base = os.path.splitext(fname)[0]
            file_id = f"{tape_dir_name}_{file_id_base}"
            
            # Kaldiがどこからでも音声を読み込めるように、絶対パスに変換
            abs_wav_path = os.path.abspath(wav_path)
            
            # Kaldiフォーマットで書き込み
            out.write(f'{file_id} {abs_wav_path}\n')
            
    sort_file(out_fname)


if __name__ == "__main__":
    # --- ディレクトリ設定 ---
    # スクリプト自身の場所(tts1)を基準にする
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir    = os.path.join(script_dir, 'data')
    train_dir   = os.path.join(data_dir, 'train')
    eval_dir    = os.path.join(data_dir, 'eval')
    
    # 音声データ本体の場所 (tree.txt に合わせて ver20221208 を指定)
    original_wav_dir  = os.path.join(script_dir, 'data/ver20221208/speech')
    
    # tapeディレクトリの下のWAVファイルをすべて取得
    wav_data_paths = glob.glob(os.path.join(original_wav_dir, 'tape*', '*.wav'))
    
    if len(wav_data_paths) == 0:
        print(f"Error: {original_wav_dir} にWAVファイルが見つかりません。")
        sys.exit(1)

    print(f"Total WAV files found: {len(wav_data_paths)}")

    # データの分割 (今回はevalを10ファイルに設定。必要に応じて変更してください)
    train_wav_list, eval_wav_list = train_test_split(wav_data_paths, test_size=10, random_state=32)
    
    # wav.scp の作成
    print("Generating wav.scp files...")
    make_wavscp(train_wav_list, train_dir)
    make_wavscp(eval_wav_list, eval_dir)

    print("Success! data/train/wav.scp and data/eval/wav.scp are ready.")