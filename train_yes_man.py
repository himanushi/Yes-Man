"""
Yes-Man カスタムウェイクワードモデル学習スクリプト
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """学習環境のセットアップ"""
    print("🔧 Setting up training environment...")
    
    # openWakeWordディレクトリに移動
    oww_path = Path("openWakeWord")
    if not oww_path.exists():
        print("❌ openWakeWord directory not found. Please clone the repository first.")
        return False
    
    os.chdir(oww_path)
    
    # pipで直接必要なパッケージをインストール
    required_packages = [
        "torch", "torchaudio", "torchvision", 
        "numpy", "scipy", "librosa", "soundfile",
        "speechbrain", "datasets", 
        "pyyaml", "torchinfo", "torchmetrics",
        "pronouncing==0.2.0",
        "audiomentations", "torch-audiomentations",
        "mutagen", "acoustics",
        "webrtcvad", "resampy", "pedalboard",
        "matplotlib"
    ]
    
    print("📦 Installing required packages...")
    for package in required_packages:
        subprocess.run([sys.executable, "-m", "pip", "install", package], 
                      capture_output=True)
    
    # openWakeWordを開発モードでインストール
    print("📦 Installing openWakeWord in development mode...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                  capture_output=True)
    
    print("✅ Environment setup complete!")
    return True

def generate_training_config():
    """Yes-Man用の学習設定ファイル生成"""
    config_content = """
model_name: "yes_man"
target_phrase:
  - "yes man"
  - "yesman"

n_samples: 10000  # Start with smaller dataset for testing
n_samples_val: 2000
tts_batch_size: 50
augmentation_batch_size: 16

piper_sample_generator_path: "./piper-sample-generator"
output_dir: "./yes_man_model_output"

# You'll need to download these datasets
rir_paths: []
background_paths: []
background_paths_duplication_rate: []

# Skip validation data for now
false_positive_validation_data_path: null

augmentation_rounds: 1

# Skip external data for basic training
feature_data_files: {}

batch_n_per_class:
  "positive": 100

model_type: "dnn"
layer_size: 32

steps: 10000
max_negative_weight: 1000
target_false_positives_per_hour: 0.5
"""
    
    config_path = Path("yes_man_config.yml")
    config_path.write_text(config_content)
    print(f"✅ Training config saved to: {config_path}")
    return str(config_path)

def train_model():
    """モデル学習実行"""
    if not setup_environment():
        return
    
    config_path = generate_training_config()
    
    print("\n" + "="*50)
    print("🚀 Starting Yes-Man wake word model training")
    print("="*50)
    
    # Step 1: Generate synthetic clips
    print("\n📢 Step 1: Generating synthetic audio clips...")
    print("Note: This step requires piper-sample-generator.")
    print("If it fails, you may need to manually generate training data.")
    
    cmd = [sys.executable, "openwakeword/train.py", 
           "--training_config", config_path, 
           "--generate_clips"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Clips generated successfully!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Clip generation failed: {e}")
        print("You may need to manually prepare training data.")
    
    # Step 2: Augment clips
    print("\n🎵 Step 2: Augmenting audio clips...")
    cmd = [sys.executable, "openwakeword/train.py", 
           "--training_config", config_path, 
           "--augment_clips"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Clips augmented successfully!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Augmentation failed: {e}")
    
    # Step 3: Train model
    print("\n🧠 Step 3: Training the model...")
    cmd = [sys.executable, "openwakeword/train.py", 
           "--training_config", config_path, 
           "--train_model"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Model trained successfully!")
        print(f"📁 Model saved to: yes_man_model_output/")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Training failed: {e}")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║  Yes-Man Wake Word Model Training Tool   ║
    ╚══════════════════════════════════════════╝
    """)
    
    train_model()