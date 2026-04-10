import os
import sys
import glob
import subprocess
import re
import MeCab
import unidic_lite
from sklearn.model_selection import train_test_split

def sort_file(fname):
    """Kaldi/ESPnet必須のLC_ALL=Cソート"""
    subprocess.call(f'export LC_ALL=C; sort "{fname}" > "{fname}.sorted"', shell=True)
    subprocess.call(f'rm "{fname}"', shell=True)
    subprocess.call(f'mv "{fname}.sorted" "{fname}"', shell=True)

def clean_text(text):
    """
    音声合成に不要なコーパス特有の記号やルビを削除します
    例: ｜昔々［むかしむかし］ -> 昔々
    """
    # 1. ［ ］とその中身（ルビ）を削除
    text = re.sub(r'［.*?］', '', text)
    # 2. ｜（ルビの開始記号）を削除
    text = text.replace('｜', '')
    # 3. （ ）とその中身（言い淀みや注釈）を削除
    text = re.sub(r'（.*?）', '', text)
    # 4. ＊ などのコーパス特有の記号を削除
    text = text.replace('＊', '')
    # 5. 半角・全角スペースの整理
    text = text.replace('　', ' ').strip()
    return text

def make_transcript_and_text(transcript_paths, train_dir, eval_dir, eval_wav_paths):
    """
    transcriptファイルとtextファイルを同時に作成します
    """
    # 半角から全角への変換
    ZEN = "".join(chr(0xff01 + i) for i in range(94))
    HAN = "".join(chr(0x21 + i) for i in range(94))
    HAN2ZEN = str.maketrans(HAN, ZEN)

    # eval用のIDリストを作成（wav.scpと同じロジック）
    eval_utt_id_list = []
    for eval_wav in eval_wav_paths:
        tape_dir = os.path.basename(os.path.dirname(eval_wav))
        fname = os.path.basename(eval_wav)
        file_id_base = os.path.splitext(fname)[0]
        eval_utt_id_list.append(f"{tape_dir}_{file_id_base}")

    # 出力先ディレクトリの作成
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)

    # 出力ファイル名
    train_transcript_fname = f'{train_dir}/transcript'
    eval_transcript_fname  = f'{eval_dir}/transcript'
    train_text_fname       = f'{train_dir}/text'
    eval_text_fname        = f'{eval_dir}/text'

    # unidic-liteの辞書パスを自動指定してMeCabを初期化
    try:
        chasen_tagger = MeCab.Tagger(f"-d {unidic_lite.DICDIR}")
    except RuntimeError:
        print("Error: MeCabの辞書が見つかりません。")
        sys.exit(1)

    with open(train_transcript_fname, 'w', encoding='utf-8') as out_tr_trans, \
         open(eval_transcript_fname, 'w', encoding='utf-8') as out_ev_trans, \
         open(train_text_fname, 'w', encoding='utf-8') as out_tr_text, \
         open(eval_text_fname, 'w', encoding='utf-8') as out_ev_text:
             
        for csv_path in transcript_paths:
            # IDの作成 (tape001_00_吉野の石落し など)
            tape_dir_name = os.path.basename(os.path.dirname(csv_path))
            fname = os.path.basename(csv_path)
            file_id_base = os.path.splitext(fname)[0]
            utt_id = f"{tape_dir_name}_{file_id_base}"

            # 生のテキストを読み込み、不要な記号を掃除する
            with open(csv_path, 'r', encoding='utf-8') as trans:
                raw_text = trans.read().strip()
                
            cleaned_text = clean_text(raw_text)
            transcript = cleaned_text.translate(HAN2ZEN)
            transcript = transcript.replace('・',' ').replace('－',' ').replace('』',' ').replace('『',' ').replace('」',' ').replace('「',' ')
            
            node = chasen_tagger.parseToNode(transcript)
            transcript_line = []
            text_line = []
            
            while node:
                feature = node.feature
                if feature != 'BOS/EOS,*,*,*,*,*,*,*,*':
                    surface = node.surface
                    
                    if surface in ['、', '。', '，', '．']:
                        transcript_line.append('<sp>')
                        text_line.append('<sp>')
                    elif surface.strip() != '':
                        split_feature = feature.split(',')
                        
                        # UniDicではカナ読みは基本的にインデックス9番目に格納される
                        reading = split_feature[9] if len(split_feature) > 9 else '*'
                        if reading == '':
                            reading = '*'
                            
                        # 品詞情報の取得 (例: 名詞/普通名詞)
                        part_of_speech = f"{split_feature[0]}/{split_feature[1]}" if len(split_feature) > 1 else split_feature[0]
                        
                        # transcript用 (単語+読み+品詞)
                        transcript_line.append(f'{surface}+{reading}+{part_of_speech}')
                        # text用 (単語+品詞)
                        text_line.append(f'{surface}+{part_of_speech}')
                        
                node = node.next
                
            # 文末の <sp> は削除する (参考コードのロジック)
            if transcript_line and transcript_line[-1] == '<sp>':
                transcript_line.pop()
            if text_line and text_line[-1] == '<sp>':
                text_line.pop()
                
            transcript_line_str = ' '.join(transcript_line)
            text_line_str = ' '.join(text_line)
            
            # evalかtrainかで振り分けて書き込み
            if utt_id in eval_utt_id_list:
                out_ev_trans.write(f'{utt_id} {transcript_line_str}\n')
                out_ev_text.write(f'{utt_id} {text_line_str}\n')
            else:
                out_tr_trans.write(f'{utt_id} {transcript_line_str}\n')
                out_tr_text.write(f'{utt_id} {text_line_str}\n')
                
    # Kaldi必須のソート
    sort_file(train_transcript_fname)
    sort_file(eval_transcript_fname)
    sort_file(train_text_fname)
    sort_file(eval_text_fname)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir   = os.path.join(script_dir, 'data')
    train_dir  = os.path.join(data_dir, 'train')
    eval_dir   = os.path.join(data_dir, 'eval')
    
    # データ配置場所 (dataディレクトリの中に変更)
    original_wav_dir = os.path.join(data_dir, 'ver20221208/speech')
    transcript_base_dir = os.path.join(data_dir, 'ver20221208/transcript/utf8')
    
    # 1. wav.scpの時と完全に同じようにWAVファイルを分割してevalのリストを作る
    wav_data_paths = glob.glob(os.path.join(original_wav_dir, 'tape*', '*.wav'))
    train_wav_list, eval_wav_list = train_test_split(wav_data_paths, test_size=10, random_state=32)
    
    # 2. 書き起こし(CSV)ファイルの取得
    transcript_paths = glob.glob(os.path.join(transcript_base_dir, 'tape*', '*.csv'))
    
    if len(transcript_paths) == 0:
        print(f"Error: {transcript_base_dir} にCSVが見つかりません。")
        sys.exit(1)
        
    print("Cleaning text, parsing with MeCab (unidic-lite), and generating files...")
    make_transcript_and_text(transcript_paths, train_dir, eval_dir, eval_wav_list)
    print("Success! 'transcript' and 'text' files are generated in data/train and data/eval.")