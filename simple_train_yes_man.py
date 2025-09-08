"""
Yes-Man簡易学習スクリプト（依存関係問題回避版）
"""

import os
import sys
import torch
import numpy as np
from pathlib import Path

# openWakeWordをパスに追加
sys.path.insert(0, 'openWakeWord')

def create_simple_training_data():
    """簡易的な学習データ作成"""
    print("📊 Creating simple training data for Yes-Man...")
    
    # ダミーの音声特徴量を生成（実際の学習には実データが必要）
    # これは概念実証用
    
    output_dir = Path("yes_man_training_data")
    output_dir.mkdir(exist_ok=True)
    
    # 正例データ（Yes-Man）のダミー特徴量
    positive_features = np.random.randn(1000, 16, 96)  # 1000サンプル
    np.save(output_dir / "positive_features.npy", positive_features)
    
    # 負例データのダミー特徴量
    negative_features = np.random.randn(5000, 16, 96)  # 5000サンプル
    np.save(output_dir / "negative_features.npy", negative_features)
    
    print(f"✅ Training data saved to {output_dir}")
    return output_dir

def train_simple_model():
    """簡易モデル学習"""
    import torch.nn as nn
    import torch.optim as optim
    
    print("🧠 Training simple Yes-Man detection model...")
    
    # データ読み込み
    data_dir = create_simple_training_data()
    positive = np.load(data_dir / "positive_features.npy")
    negative = np.load(data_dir / "negative_features.npy")
    
    # データ準備
    X = np.vstack([positive, negative])
    y = np.array([1] * len(positive) + [0] * len(negative))
    
    # シャッフル
    indices = np.random.permutation(len(X))
    X = X[indices]
    y = y[indices]
    
    # PyTorchテンソルに変換
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.FloatTensor(y).unsqueeze(1)
    
    # 簡単なニューラルネットワーク定義
    class WakeWordModel(nn.Module):
        def __init__(self, input_size=16*96):
            super().__init__()
            self.flatten = nn.Flatten()
            self.fc1 = nn.Linear(input_size, 64)
            self.bn1 = nn.BatchNorm1d(64)
            self.relu1 = nn.ReLU()
            self.fc2 = nn.Linear(64, 32)
            self.bn2 = nn.BatchNorm1d(32)
            self.relu2 = nn.ReLU()
            self.fc3 = nn.Linear(32, 1)
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x):
            x = self.flatten(x)
            x = self.relu1(self.bn1(self.fc1(x)))
            x = self.relu2(self.bn2(self.fc2(x)))
            x = self.sigmoid(self.fc3(x))
            return x
    
    # モデル初期化
    model = WakeWordModel()
    
    # GPU使用可能なら使用
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    X_tensor = X_tensor.to(device)
    y_tensor = y_tensor.to(device)
    
    print(f"📍 Using device: {device}")
    
    # 学習設定
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    
    # 学習ループ
    batch_size = 32
    epochs = 10
    
    for epoch in range(epochs):
        total_loss = 0
        for i in range(0, len(X_tensor), batch_size):
            batch_X = X_tensor[i:i+batch_size]
            batch_y = y_tensor[i:i+batch_size]
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss:.4f}")
    
    # モデル保存
    output_path = Path("yes_man_model.pth")
    torch.save(model.state_dict(), output_path)
    print(f"✅ Model saved to {output_path}")
    
    # ONNXエクスポート
    model.eval()
    dummy_input = torch.randn(1, 16, 96).to(device)
    onnx_path = Path("yes_man_model.onnx")
    
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=11,
        input_names=['audio_features'],
        output_names=['wake_word_probability'],
        dynamic_axes={'audio_features': {0: 'batch_size'}}
    )
    
    print(f"✅ ONNX model exported to {onnx_path}")
    print("\n🎉 Training complete! Note: This is a simplified demo.")
    print("For production use, you need:")
    print("1. Real audio data collection")
    print("2. Proper TTS-based synthetic data generation")
    print("3. Audio augmentation pipeline")
    print("4. Extensive validation")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║  Yes-Man簡易学習デモ (Windows対応版)     ║
    ╚══════════════════════════════════════════╝
    """)
    
    train_simple_model()