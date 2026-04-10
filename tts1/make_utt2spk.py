import os
import sys
import glob
import subprocess

def sort_file(fname):
    """Kaldi/ESPnet必須のLC_ALL=Cソート"""
    subprocess.call(f'export LC_ALL=C; sort "{fname}" > "{fname}.sorted"', shell=True)
    subprocess.call(f'rm "{fname}"', shell=True)
    subprocess.call(f'mv "{fname}.sorted" "{fname}"', shell=True)

def create_speaker_dict(meta_info_dir):
    """
    meta_infoのCSVを読み込み、{utt_id: 話者ID} の辞書を作成します
    """
    speaker_dict = {}
    csv_paths = glob.glob(os.path.join(meta_info_dir, '*.csv'))
    
    if not csv_paths:
        print(f"Warning: {meta_info_dir} にCSVファイルが見つかりません。")
        return speaker_dict

    for csv_path in csv_paths:
        # CSVファイル名からテープ名を抽出 (例: tape001.csv -> tape001)
        tape_name = os.path.splitext(os.path.basename(csv_path))[0]
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 空行やヘッダー行はスキップ
                if not line or line.startswith('昔話の題目'):
                    continue
                
                parts = line.split(',')
                # カンマ区切りで少なくとも8要素あるはず
                if len(parts) >= 8:
                    # インデックス3番目が「話者符号 (F001など)」
                    speaker_id = parts[3]
                    # 一番最後が「ファイル名 (00_吉野の石落し など)」
                    file_name_base = parts[-1] 
                    
                    # textやwav.scpと同じutt_idを作成して紐付け
                    utt_id = f"{tape_name}_{file_name_base}"
                    speaker_dict[utt_id] = speaker_id
                    
    return speaker_dict

def make_utt2spk(directory, speaker_dict):
    """
    text ファイルを読み込み、utt2spk を作成します
    """
    text_fname = os.path.join(directory, 'text')
    out_utt2spk_fname = os.path.join(directory, 'utt2spk')

    if not os.path.exists(text_fname):
        print(f"Warning: {text_fname} が見つかりません。スキップします。")
        return

    with open(text_fname, 'r', encoding='utf-8') as text_f, \
         open(out_utt2spk_fname, 'w', encoding='utf-8') as out_f:
             
        for line in text_f:
            line = line.strip()
            if not line:
                continue
                
            # 先頭の発話ID(utt_id)だけを取得
            utt_id = line.split(' ')[0]
            
            # 辞書から話者IDを取得。万が一CSVに見つからなかった場合は 'unknown_speaker'
            speaker_id = speaker_dict.get(utt_id, "unknown_speaker")
            
            # 発話IDと話者IDをスペース区切りで書き込み
            out_f.write(f'{utt_id} {speaker_id}\n')

    # Kaldi必須のソート
    sort_file(out_utt2spk_fname)
    print(f"Created: {out_utt2spk_fname}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir   = os.path.join(script_dir, 'data')
    train_dir  = os.path.join(data_dir, 'train')
    eval_dir   = os.path.join(data_dir, 'eval')
    
    # メタ情報(CSV)のディレクトリ
    meta_info_dir = os.path.join(data_dir, 'ver20221208/meta_info/utf8')

    print("Reading meta_info to map speaker IDs...")
    speaker_dict = create_speaker_dict(meta_info_dir)
    print(f"Loaded {len(speaker_dict)} speaker mappings from CSV.")

    print("Generating utt2spk files...")
    make_utt2spk(train_dir, speaker_dict)
    make_utt2spk(eval_dir, speaker_dict)
    
    print("Success! utt2spk files are ready.")