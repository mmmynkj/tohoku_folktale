import os
import sys
import glob
import subprocess
import re
from sklearn.model_selection import train_test_split

def sort_file(fname):
    """Kaldi/ESPnet必須のLC_ALL=Cソート"""
    subprocess.call(f'export LC_ALL=C; sort "{fname}" > "{fname}.sorted"', shell=True)
    subprocess.call(f'rm "{fname}"', shell=True)
    subprocess.call(f'mv "{fname}.sorted" "{fname}"', shell=True)

def clean_text(text):
    """
    音声合成に不要な記号、ルビ、見えない改行コードを完全に削除します
    """
    # ★最重要: 悪さをする改行コード(\r, \n)を完全にスペースに置換
    text = text.replace('\r', ' ').replace('\n', ' ')
    
    # ［ ］とその中身（ルビ）を削除
    text = re.sub(r'［.*?］', '', text)
    # ｜（ルビの開始記号）を削除
    text = text.replace('｜', '')
    # （ ）とその中身（言い淀みや注釈）を削除
    text = re.sub(r'（.*?）', '', text)
    # ＊ などのコーパス特有の記号を削除
    text = text.replace('＊', '')
    
    # 複数の連続するスペースを1つにまとめ、前後の空白を削除
    text = text.replace('　', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_text(transcript_paths, train_dir, eval_dir, eval_wav_paths):
    # 半角から全角への変換
    ZEN = "".join(chr(0xff01 + i) for i in range(94))
    HAN = "".join(chr(0x21 + i) for i in range(94))
    HAN2ZEN = str.maketrans(HAN, ZEN)

    # eval用のIDリストを作成
    eval_utt_id_list = []
    for eval_wav in eval_wav_paths:
        tape_dir = os.path.basename(os.path.dirname(eval_wav))
        fname = os.path.basename(eval_wav)
        file_id_base = os.path.splitext(fname)[0]
        eval_utt_id_list.append(f"{tape_dir}_{file_id_base}")

    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)

    train_text_fname = f'{train_dir}/text'
    eval_text_fname  = f'{eval_dir}/text'

    sample_printed = False

    with open(train_text_fname, 'w', encoding='utf-8') as out_tr, \
         open(eval_text_fname, 'w', encoding='utf-8') as out_ev:
             
        for csv_path in transcript_paths:
            # IDの作成 (tape001_00_吉野の石落し など)
            tape_dir_name = os.path.basename(os.path.dirname(csv_path))
            fname = os.path.basename(csv_path)
            file_id_base = os.path.splitext(fname)[0]
            utt_id = f"{tape_dir_name}_{file_id_base}"

            # テキストの読み込みと掃除
            with open(csv_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            cleaned_text = clean_text(raw_text)
            
            transcript = cleaned_text.translate(HAN2ZEN)
            transcript = transcript.replace('・',' ').replace('－',' ').replace('』',' ').replace('『',' ').replace('」',' ').replace('「',' ')
            
            # 万が一CSVに「ID: テキスト」や「ID, テキスト」の形でID自体が含まれていた場合、テキスト部分だけを抜く
            if transcript.startswith(utt_id):
                if ':' in transcript:
                    transcript = transcript.split(':', 1)[1].strip()
                elif ',' in transcript:
                    transcript = transcript.split(',', 1)[1].strip()

            # 確実なKaldiフォーマットの構成: UTT_ID + 半角スペース + テキスト
            output_line = f"{utt_id} {transcript}\n"
            
            if not sample_printed:
                print("--- サンプル出力の確認 ---")
                print(output_line.strip())
                print("--------------------------")
                sample_printed = True

            if utt_id in eval_utt_id_list:
                out_ev.write(output_line)
            else:
                out_tr.write(output_line)
                
    sort_file(train_text_fname)
    sort_file(eval_text_fname)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir   = os.path.join(script_dir, 'data')
    train_dir  = os.path.join(data_dir, 'train')
    eval_dir   = os.path.join(data_dir, 'eval')
    
    original_wav_dir = os.path.join(data_dir, 'ver20221208/speech')
    transcript_base_dir = os.path.join(data_dir, 'ver20221208/transcript/utf8')
    
    wav_data_paths = glob.glob(os.path.join(original_wav_dir, 'tape*', '*.wav'))
    train_wav_list, eval_wav_list = train_test_split(wav_data_paths, test_size=10, random_state=32)
    
    transcript_paths = glob.glob(os.path.join(transcript_base_dir, 'tape*', '*.csv'))
    
    if len(transcript_paths) == 0:
        print(f"Error: {transcript_base_dir} にCSVが見つかりません。")
        sys.exit(1)
        
    print(f"Total transcript files found: {len(transcript_paths)}")
    print("Generating strictly formatted 'text' files...")
    
    make_text(transcript_paths, train_dir, eval_dir, eval_wav_list)
    print("Success! text files are ready.")