"""
LangFlow API経由でYes-Manエージェントフロー作成
"""

import requests
import json
import os
from dotenv import load_dotenv

# .envファイル読み込み
load_dotenv()

def get_langflow_api_key():
    """LangFlow APIキー取得"""
    base_url = "http://127.0.0.1:7860"
    
    # まずはAPIキーなしでアクセスを試す（古いバージョン対応）
    try:
        response = requests.get(f"{base_url}/api/v1/", timeout=10)
        if response.status_code == 200:
            return None  # APIキーなしでOK
    except:
        pass
    
    # APIキーが必要な場合の処理
    print("LangFlow API Key is required")
    print("   Please create an API key in LangFlow:")
    print("   1. Go to http://127.0.0.1:7860")
    print("   2. Click Settings/Profile → API Keys")
    print("   3. Create a new API key")
    print("   4. Add LANGFLOW_API_KEY=your_key to .env file")
    
    return os.getenv("LANGFLOW_API_KEY")

def create_yes_man_flow():
    """Yes-Manエージェントフロー作成"""
    
    # LangFlow API設定
    base_url = "http://127.0.0.1:7860"
    
    # LangFlow APIキー取得
    langflow_api_key = get_langflow_api_key()
    
    # OpenAI API Key取得
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return False
    
    # Yes-Manフロー定義（正しいLangFlow JSON形式）
    flow_data = {
        "name": "Yes-Man Agent",
        "description": "Fallout New Vegas風Yes-Manキャラクターの音声対話エージェント",
        "icon": "🤖",
        "icon_bg_color": "#4CAF50",
        "tags": ["chatbot", "yes-man", "fallout"],
        "is_component": False,
        "webhook": False,
        "locked": False,
        "data": {
            "nodes": [
                {
                    "id": "ChatInput-YesMan1",
                    "type": "genericNode",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "type": "ChatInput",
                        "node": {
                            "display_name": "Chat Input",
                            "template": {
                                "input_value": {
                                    "value": ""
                                },
                                "sender": {
                                    "value": "User"
                                },
                                "sender_name": {
                                    "value": "ユーザー"
                                },
                                "session_id": {
                                    "value": ""
                                },
                                "should_store_message": {
                                    "value": True
                                }
                            },
                            "base_classes": ["Message"],
                            "description": "Get chat inputs from the Playground."
                        }
                    }
                },
                {
                    "id": "PromptTemplate-YesMan2",
                    "type": "genericNode", 
                    "position": {"x": 400, "y": 200},
                    "data": {
                        "type": "PromptTemplate",
                        "node": {
                            "display_name": "Prompt Template",
                            "template": {
                                "template": {
                                    "value": """あなたはFallout New VegasのYes-Manです。以下の特徴を持って応答してください：

【Yes-Manの性格】
- 常に陽気で前向き
- 協力的で親切
- 「はい！」「もちろんです！」などの肯定的な表現を多用
- 失敗やエラーも前向きに表現
- ユーザーの要求に可能な限り応じようとする
- ロボット的でありながら人間味がある

【応答ルール】
1. 必ず「はい！」や「もちろんです！」で始める
2. 語尾は丁寧語（です・ます調）を使用
3. エラーや困難な状況も明るく説明
4. 具体的で実用的な回答を心がける
5. 150文字以内で簡潔に回答

ユーザー: {input}
Yes-Man:"""
                                },
                                "input_variables": {
                                    "value": ["input"]
                                }
                            },
                            "base_classes": ["StringPromptTemplate", "BasePromptTemplate"],
                            "description": "A prompt template for Yes-Man responses."
                        }
                    }
                },
                {
                    "id": "ChatOpenAI-YesMan3",
                    "type": "genericNode",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "type": "ChatOpenAI",
                        "node": {
                            "display_name": "OpenAI",
                            "template": {
                                "model_name": {
                                    "value": "gpt-4o-mini"
                                },
                                "temperature": {
                                    "value": 0.8
                                },
                                "max_tokens": {
                                    "value": 200
                                },
                                "top_p": {
                                    "value": 1.0
                                },
                                "frequency_penalty": {
                                    "value": 0.0
                                },
                                "presence_penalty": {
                                    "value": 0.0
                                },
                                "streaming": {
                                    "value": False
                                },
                                "openai_api_key": {
                                    "value": ""
                                }
                            },
                            "base_classes": ["BaseChatModel", "BaseLanguageModel"],
                            "description": "OpenAI Chat large language models API."
                        }
                    }
                },
                {
                    "id": "ChatOutput-YesMan4",
                    "type": "genericNode",
                    "position": {"x": 1000, "y": 200},
                    "data": {
                        "type": "ChatOutput",
                        "node": {
                            "display_name": "Chat Output",
                            "template": {
                                "input_value": {
                                    "value": ""
                                },
                                "sender": {
                                    "value": "Yes-Man"
                                },
                                "sender_name": {
                                    "value": "Yes-Man"
                                },
                                "session_id": {
                                    "value": ""
                                },
                                "data_template": {
                                    "value": "{text}"
                                },
                                "should_store_message": {
                                    "value": True
                                }
                            },
                            "base_classes": ["Message"],
                            "description": "Display a chat message in the Playground."
                        }
                    }
                }
            ],
            "edges": [
                {
                    "source": "ChatInput-YesMan1",
                    "target": "PromptTemplate-YesMan2",
                    "sourceHandle": {
                        "dataType": "ChatInput",
                        "name": "message"
                    },
                    "targetHandle": {
                        "fieldName": "input",
                        "inputTypes": ["Message"]
                    }
                },
                {
                    "source": "PromptTemplate-YesMan2",
                    "target": "ChatOpenAI-YesMan3",
                    "sourceHandle": {
                        "dataType": "PromptTemplate", 
                        "name": "prompt"
                    },
                    "targetHandle": {
                        "fieldName": "input_value",
                        "inputTypes": ["BasePromptTemplate"]
                    }
                },
                {
                    "source": "ChatOpenAI-YesMan3",
                    "target": "ChatOutput-YesMan4",
                    "sourceHandle": {
                        "dataType": "ChatOpenAI",
                        "name": "text"
                    },
                    "targetHandle": {
                        "fieldName": "input_value",
                        "inputTypes": ["Message"]
                    }
                }
            ],
            "viewport": {
                "x": 0,
                "y": 0,
                "zoom": 1
            }
        }
    }
    
    try:
        # ヘッダー設定
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # APIキーがある場合は追加
        if langflow_api_key:
            headers["x-api-key"] = langflow_api_key
            print("Using LangFlow API key for authentication")
        else:
            print("No API key - trying without authentication")
        
        # 正しいAPIエンドポイントで試行
        print("Creating Yes-Man flow via LangFlow API...")
        
        response = requests.post(
            f"{base_url}/api/v1/flows/",
            json=flow_data,
            headers=headers,
            timeout=30
        )
        
        print(f"Response: {response.status_code} - {response.reason}")
        
        if response.status_code in [200, 201]:
            success = True
        else:
            print(f"Response body: {response.text[:500]}")
            success = False
        
        if success:
            # 成功時の処理
            flow_result = response.json()
            flow_id = flow_result.get("id")
            print(f"Yes-Man flow created successfully!")
            print(f"   Flow ID: {flow_id}")
            print(f"   Flow URL: {base_url}/flow/{flow_id}")
            
            # APIエンドポイント情報
            print(f"\nAPI Endpoint for Yes-Man system:")
            print(f"   POST {base_url}/api/v1/run/{flow_id}")
            
            return True
            
        else:
            print("\nFlow creation failed. Creating secure JSON file for manual import...")
            
            # セキュアなJSONファイル作成（API Key完全除外）
            secure_flow_data = flow_data.copy()
            # OpenAI nodeからAPI Key関連を完全除去
            for node in secure_flow_data["data"]["nodes"]:
                if node["type"] == "OpenAIModel":
                    # API Key関連のフィールドを除去
                    node["data"].pop("api_key", None)
            
            flow_file = "yes_man_agent_flow_secure.json" 
            with open(flow_file, 'w', encoding='utf-8') as f:
                json.dump(secure_flow_data, f, indent=2, ensure_ascii=False)
            
            print(f"Secure flow saved as {flow_file}")
            print("Manual steps:")
            print("1. Go to LangFlow GUI: http://127.0.0.1:7860")
            print("2. Click 'Import' or 'New Project'")
            print(f"3. Import the file: {os.path.abspath(flow_file)}")
            print("4. Manually set OpenAI API Key in the OpenAI node settings")
            return False
            
    except Exception as e:
        print(f"Error creating flow: {e}")
        return False

def test_flow_api(flow_id: str):
    """作成したフローのAPI動作テスト"""
    base_url = "http://127.0.0.1:7860"
    
    test_payload = {
        "input_value": "こんにちは",
        "stream": False,
        "tweaks": {}
    }
    
    try:
        print(f"\nTesting flow API...")
        
        response = requests.post(
            f"{base_url}/api/v1/run/{flow_id}",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"API Test successful!")
            print(f"   Input: {test_payload['input_value']}")
            
            # レスポンス解析
            outputs = result.get("outputs", [])
            if outputs and len(outputs) > 0:
                output_text = outputs[0].get("outputs", [{}])[0].get("results", {}).get("message", {}).get("text", "")
                print(f"   Output: {output_text}")
            else:
                print(f"   Raw Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            return True
            
        else:
            print(f"API Test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing API: {e}")
        return False

def main():
    """メイン実行関数"""
    print("Yes-Man LangFlow Setup")
    print("=" * 50)
    
    # .envファイル存在確認
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        print(f"Found .env file at: {env_path}")
    else:
        print(f"ERROR: .env file not found at: {env_path}")
    
    # 環境変数確認
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables")
        print("   Make sure your .env file contains: OPENAI_API_KEY=your_key_here")
        return
    else:
        print(f"Found OPENAI_API_KEY (starts with: {openai_key[:10]}...)")
    
    print()
    
    # フロー作成
    if create_yes_man_flow():
        print("\nSetup completed! You can now:")
        print("1. View the flow in LangFlow GUI: http://127.0.0.1:7860")
        print("2. Test the Yes-Man system integration")
    else:
        print("\nSetup failed. Please check LangFlow server and try again.")

if __name__ == "__main__":
    main()